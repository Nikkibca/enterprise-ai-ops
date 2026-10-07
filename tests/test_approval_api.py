import pytest
from fastapi.testclient import TestClient

from app.agents.schemas import AgentPlan
from app.db import SessionLocal
from app.dependencies import get_llm_provider
from app.llm.fake import FakeLLMProvider
from app.main import app
from app.models import ApprovalRequest, AuditEvent, Task


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def override_llm_provider():
    app.dependency_overrides[get_llm_provider] = (
        lambda: FakeLLMProvider(
            AgentPlan(
                reasoning_summary="Test task workflow.",
                tool_call={
                    "tool": "sql.read",
                    "arguments": {
                        "query": (
                            "SELECT COUNT(*) "
                            "FROM payment_failures"
                        ),
                    },
                },
            )
        )
    )

    yield

    app.dependency_overrides.clear()


def cleanup_database():
    db = SessionLocal()

    try:
        db.query(ApprovalRequest).delete()
        db.query(AuditEvent).delete()
        db.query(Task).delete()
        db.commit()
    finally:
        db.close()


def create_task(client: TestClient):
    response = client.post(
        "/tasks",
        json={
            "user_id": "user-123",
            "request": "Restart payment worker",
        },
    )

    assert response.status_code == 200

    return response.json()


def test_create_approval(client):
    cleanup_database()

    task = create_task(client)

    response = client.post(
        "/approvals",
        json={
            "task_id": task["id"],
            "tool_name": "service.restart",
            "risk_level": "high",
            "requested_by": "user-123",
            "reason": (
                "High-risk operation requires human approval."
            ),
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["task_id"] == task["id"]
    assert data["tool_name"] == "service.restart"
    assert data["risk_level"] == "high"
    assert data["requested_by"] == "user-123"
    assert data["status"] == "pending"


def test_get_approval(client):
    cleanup_database()

    task = create_task(client)

    create_response = client.post(
        "/approvals",
        json={
            "task_id": task["id"],
            "tool_name": "service.restart",
            "risk_level": "high",
            "requested_by": "user-123",
            "reason": (
                "High-risk operation requires human approval."
            ),
        },
    )

    assert create_response.status_code == 201

    approval = create_response.json()

    response = client.get(
        f"/approvals/{approval['id']}",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == approval["id"]
    assert data["task_id"] == task["id"]
    assert data["status"] == "pending"


def test_approve_approval(client):
    cleanup_database()

    task = create_task(client)

    create_response = client.post(
        "/approvals",
        json={
            "task_id": task["id"],
            "tool_name": "service.restart",
            "risk_level": "high",
            "requested_by": "user-123",
            "reason": (
                "High-risk operation requires human approval."
            ),
        },
    )

    assert create_response.status_code == 201

    approval = create_response.json()

    response = client.post(
        f"/approvals/{approval['id']}/approve",
        json={
            "decided_by": "manager-123",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == approval["id"]
    assert data["status"] == "approved"
    assert data["decided_by"] == "manager-123"
    assert data["decided_at"] is not None


def test_reject_approval(client):
    cleanup_database()

    task = create_task(client)

    create_response = client.post(
        "/approvals",
        json={
            "task_id": task["id"],
            "tool_name": "service.restart",
            "risk_level": "high",
            "requested_by": "user-123",
            "reason": (
                "High-risk operation requires human approval."
            ),
        },
    )

    assert create_response.status_code == 201

    approval = create_response.json()

    response = client.post(
        f"/approvals/{approval['id']}/reject",
        json={
            "decided_by": "manager-123",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == approval["id"]
    assert data["status"] == "rejected"
    assert data["decided_by"] == "manager-123"
    assert data["decided_at"] is not None


def test_cannot_approve_already_approved_approval(client):
    cleanup_database()

    task = create_task(client)

    create_response = client.post(
        "/approvals",
        json={
            "task_id": task["id"],
            "tool_name": "service.restart",
            "risk_level": "high",
            "requested_by": "user-123",
            "reason": (
                "High-risk operation requires human approval."
            ),
        },
    )

    assert create_response.status_code == 201

    approval = create_response.json()

    first_response = client.post(
        f"/approvals/{approval['id']}/approve",
        json={
            "decided_by": "manager-123",
        },
    )

    assert first_response.status_code == 200

    second_response = client.post(
        f"/approvals/{approval['id']}/approve",
        json={
            "decided_by": "manager-123",
        },
    )

    assert second_response.status_code == 409


def test_cannot_reject_already_rejected_approval(client):
    cleanup_database()

    task = create_task(client)

    create_response = client.post(
        "/approvals",
        json={
            "task_id": task["id"],
            "tool_name": "service.restart",
            "risk_level": "high",
            "requested_by": "user-123",
            "reason": (
                "High-risk operation requires human approval."
            ),
        },
    )

    assert create_response.status_code == 201

    approval = create_response.json()

    first_response = client.post(
        f"/approvals/{approval['id']}/reject",
        json={
            "decided_by": "manager-123",
        },
    )

    assert first_response.status_code == 200

    second_response = client.post(
        f"/approvals/{approval['id']}/reject",
        json={
            "decided_by": "manager-123",
        },
    )

    assert second_response.status_code == 409


def test_approval_creates_audit_events(client):
    cleanup_database()

    task = create_task(client)

    create_response = client.post(
        "/approvals",
        json={
            "task_id": task["id"],
            "tool_name": "service.restart",
            "risk_level": "high",
            "requested_by": "user-123",
            "reason": (
                "High-risk operation requires human approval."
            ),
        },
    )

    assert create_response.status_code == 201

    approval = create_response.json()

    approve_response = client.post(
        f"/approvals/{approval['id']}/approve",
        json={
            "decided_by": "manager-123",
        },
    )

    assert approve_response.status_code == 200

    db = SessionLocal()

    try:
        events = (
            db.query(AuditEvent)
            .filter(AuditEvent.task_id == task["id"])
            .order_by(AuditEvent.id)
            .all()
        )

        event_types = [event.event_type for event in events]

        assert "approval.requested" in event_types
        assert "approval.granted" in event_types

    finally:
        db.close()