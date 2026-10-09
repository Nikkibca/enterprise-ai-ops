from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.agents.schemas import AgentPlan, ToolCall
from app.agents.state import AgentStatus
from app.auth_settings import AuthSettings
from app.db import SessionLocal
from app.dependencies import get_llm_provider
from app.llm.fake import FakeLLMProvider
from app.main import app
from app.models import ApprovalRequest, AuditEvent, Task
from app.workflow_runner import WorkflowRunner


def create_token(user_id: str) -> str:
    settings = AuthSettings()

    now = datetime.now(timezone.utc)

    return jwt.encode(
        {
            "sub": user_id,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": now + timedelta(minutes=30),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def auth_headers(user_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_token(user_id)}",
    }


def cleanup_database():
    db = SessionLocal()

    try:
        db.execute(
            text(
                """
                TRUNCATE TABLE
                    audit_events,
                    approval_requests,
                    tasks
                RESTART IDENTITY CASCADE
                """
            )
        )
        db.commit()
    finally:
        db.close()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def override_llm_provider():
    plan = AgentPlan(
        reasoning_summary=(
            "Restarting the payment worker is the appropriate "
            "operational action for the requested service."
        ),
        tool_call=ToolCall(
            tool="service.restart",
            arguments={
                "service": "payment-worker",
            },
        ),
    )

    app.dependency_overrides[get_llm_provider] = (
        lambda: FakeLLMProvider(plan)
    )

    yield

    app.dependency_overrides.pop(
        get_llm_provider,
        None,
    )


def test_get_approval(
    client,
    override_llm_provider,
):
    cleanup_database()

    headers = auth_headers("manager-123")

    task_response = client.post(
        "/tasks",
        json={
            "request": "Restart payment worker",
        },
        headers=headers,
    )

    assert task_response.status_code == 200

    task_id = task_response.json()["id"]

    approval_response = client.post(
        "/approvals",
        json={
            "task_id": task_id,
            "tool_name": "service.restart",
            "risk_level": "high",
            "reason": "High-risk operation requires human approval.",
        },
        headers=headers,
    )

    assert approval_response.status_code == 201

    approval_id = approval_response.json()["id"]

    response = client.get(
        f"/approvals/{approval_id}",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == approval_id
    assert data["task_id"] == task_id
    assert data["tool_name"] == "service.restart"
    assert data["risk_level"] == "high"
    assert data["requested_by"] == "manager-123"
    assert data["status"] == "pending"


def test_approve_approval(
    client,
    override_llm_provider,
):
    cleanup_database()

    headers = auth_headers("manager-123")

    task_response = client.post(
        "/tasks",
        json={
            "request": "Restart payment worker",
        },
        headers=headers,
    )

    assert task_response.status_code == 200

    task_id = task_response.json()["id"]

    approval_response = client.post(
        "/approvals",
        json={
            "task_id": task_id,
            "tool_name": "service.restart",
            "risk_level": "high",
            "reason": "High-risk operation requires human approval.",
        },
        headers=headers,
    )

    assert approval_response.status_code == 201

    approval_id = approval_response.json()["id"]

    response = client.post(
        f"/approvals/{approval_id}/approve",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == approval_id
    assert data["status"] == "approved"
    assert data["decided_by"] == "manager-123"
    assert data["decided_at"] is not None


def test_reject_approval(
    client,
    override_llm_provider,
):
    cleanup_database()

    headers = auth_headers("manager-123")

    task_response = client.post(
        "/tasks",
        json={
            "request": "Restart payment worker",
        },
        headers=headers,
    )

    assert task_response.status_code == 200

    task_id = task_response.json()["id"]

    approval_response = client.post(
        "/approvals",
        json={
            "task_id": task_id,
            "tool_name": "service.restart",
            "risk_level": "high",
            "reason": "High-risk operation requires human approval.",
        },
        headers=headers,
    )

    assert approval_response.status_code == 201

    approval_id = approval_response.json()["id"]

    response = client.post(
        f"/approvals/{approval_id}/reject",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == approval_id
    assert data["status"] == "rejected"
    assert data["decided_by"] == "manager-123"
    assert data["decided_at"] is not None


def test_cannot_approve_already_approved_approval(
    client,
    override_llm_provider,
):
    cleanup_database()

    headers = auth_headers("manager-123")

    task_response = client.post(
        "/tasks",
        json={
            "request": "Restart payment worker",
        },
        headers=headers,
    )

    assert task_response.status_code == 200

    task_id = task_response.json()["id"]

    approval_response = client.post(
        "/approvals",
        json={
            "task_id": task_id,
            "tool_name": "service.restart",
            "risk_level": "high",
            "reason": "High-risk operation requires human approval.",
        },
        headers=headers,
    )

    assert approval_response.status_code == 201

    approval_id = approval_response.json()["id"]

    first_response = client.post(
        f"/approvals/{approval_id}/approve",
        headers=headers,
    )

    assert first_response.status_code == 200

    second_response = client.post(
        f"/approvals/{approval_id}/approve",
        headers=headers,
    )

    assert second_response.status_code == 409

    assert (
        second_response.json()["detail"]
        == "Only pending approval requests can be approved."
    )


def test_cannot_reject_already_rejected_approval(
    client,
    override_llm_provider,
):
    cleanup_database()

    headers = auth_headers("manager-123")

    task_response = client.post(
        "/tasks",
        json={
            "request": "Restart payment worker",
        },
        headers=headers,
    )

    assert task_response.status_code == 200

    task_id = task_response.json()["id"]

    approval_response = client.post(
        "/approvals",
        json={
            "task_id": task_id,
            "tool_name": "service.restart",
            "risk_level": "high",
            "reason": "High-risk operation requires human approval.",
        },
        headers=headers,
    )

    assert approval_response.status_code == 201

    approval_id = approval_response.json()["id"]

    first_response = client.post(
        f"/approvals/{approval_id}/reject",
        headers=headers,
    )

    assert first_response.status_code == 200

    second_response = client.post(
        f"/approvals/{approval_id}/reject",
        headers=headers,
    )

    assert second_response.status_code == 409

    assert (
        second_response.json()["detail"]
        == "Only pending approval requests can be rejected."
    )


def test_approval_creates_audit_events(
    client,
    override_llm_provider,
):
    cleanup_database()

    headers = auth_headers("manager-123")

    task_response = client.post(
        "/tasks",
        json={
            "request": "Restart payment worker",
        },
        headers=headers,
    )

    assert task_response.status_code == 200

    task_id = task_response.json()["id"]

    approval_response = client.post(
        "/approvals",
        json={
            "task_id": task_id,
            "tool_name": "service.restart",
            "risk_level": "high",
            "reason": "High-risk operation requires human approval.",
        },
        headers=headers,
    )

    assert approval_response.status_code == 201

    approval_id = approval_response.json()["id"]

    approve_response = client.post(
        f"/approvals/{approval_id}/approve",
        headers=headers,
    )

    assert approve_response.status_code == 200

    db = SessionLocal()

    try:
        events = (
            db.query(AuditEvent)
            .filter(
                AuditEvent.task_id == task_id,
            )
            .order_by(AuditEvent.id)
            .all()
        )

        event_types = [
            event.event_type
            for event in events
        ]

        assert "approval.requested" in event_types
        assert "approval.granted" in event_types

    finally:
        db.close()


def test_approve_workflow_resumes_and_completes(
    client,
    override_llm_provider,
):
    cleanup_database()

    headers = auth_headers("manager-123")

    task_response = client.post(
        "/tasks",
        json={
            "request": "Restart payment worker",
        },
        headers=headers,
    )

    assert task_response.status_code == 200

    task = task_response.json()

    assert task["status"] == "awaiting_approval"

    task_id = task["id"]

    approval_response = client.post(
        "/approvals",
        json={
            "task_id": task_id,
            "tool_name": "service.restart",
            "risk_level": "high",
            "reason": "High-risk operation requires human approval.",
        },
        headers=headers,
    )

    assert approval_response.status_code == 201

    approval_id = approval_response.json()["id"]

    approve_response = client.post(
        f"/approvals/{approval_id}/approve",
        headers=headers,
    )

    assert approve_response.status_code == 200

    final_task_response = client.get(
        f"/tasks/{task_id}",
        headers=headers,
    )

    assert final_task_response.status_code == 200

    final_task = final_task_response.json()

    assert final_task["status"] == "completed"


def test_create_approval_requires_authentication(
    client,
    override_llm_provider,
):
    cleanup_database()

    response = client.post(
        "/approvals",
        json={
            "task_id": 999999,
            "tool_name": "service.restart",
            "risk_level": "high",
            "reason": "High-risk operation requires human approval.",
        },
    )

    assert response.status_code == 401


def test_create_approval_uses_authenticated_user_as_requester(
    client,
    override_llm_provider,
):
    cleanup_database()

    headers = auth_headers("manager-123")

    task_response = client.post(
        "/tasks",
        json={
            "request": "Restart payment worker",
        },
        headers=headers,
    )

    assert task_response.status_code == 200

    task_id = task_response.json()["id"]

    response = client.post(
        "/approvals",
        json={
            "task_id": task_id,
            "tool_name": "service.restart",
            "risk_level": "high",
            "reason": "High-risk operation requires human approval.",
        },
        headers=headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["requested_by"] == "manager-123"


def test_get_approval_requires_authentication(
    client,
    override_llm_provider,
):
    cleanup_database()

    response = client.get(
        "/approvals/999999",
    )

    assert response.status_code == 401


def test_get_approval_denies_unrelated_user(
    client,
    override_llm_provider,
):
    cleanup_database()

    owner_headers = auth_headers("manager-123")

    task_response = client.post(
        "/tasks",
        json={
            "request": "Restart payment worker",
        },
        headers=owner_headers,
    )

    assert task_response.status_code == 200

    task_id = task_response.json()["id"]

    approval_response = client.post(
        "/approvals",
        json={
            "task_id": task_id,
            "tool_name": "service.restart",
            "risk_level": "high",
            "reason": "High-risk operation requires human approval.",
        },
        headers=owner_headers,
    )

    assert approval_response.status_code == 201

    approval_id = approval_response.json()["id"]

    unrelated_headers = auth_headers("user-123")

    response = client.get(
        f"/approvals/{approval_id}",
        headers=unrelated_headers,
    )

    assert response.status_code == 403

    assert (
        response.json()["detail"]
        == "User is not authorized to view this approval."
    )


def test_operations_engineer_cannot_approve_high_risk_action(
    client,
    override_llm_provider,
):
    cleanup_database()

    manager_headers = auth_headers("manager-123")

    task_response = client.post(
        "/tasks",
        json={
            "request": "Restart payment worker",
        },
        headers=manager_headers,
    )

    assert task_response.status_code == 200

    task_id = task_response.json()["id"]

    approval_response = client.post(
        "/approvals",
        json={
            "task_id": task_id,
            "tool_name": "service.restart",
            "risk_level": "high",
            "reason": "High-risk operation requires human approval.",
        },
        headers=manager_headers,
    )

    assert approval_response.status_code == 201

    approval_id = approval_response.json()["id"]

    engineer_headers = auth_headers("user-123")

    response = client.post(
        f"/approvals/{approval_id}/approve",
        headers=engineer_headers,
    )

    assert response.status_code == 403

    assert (
        response.json()["detail"]
        == (
            "User does not have permission to approve "
            "operational restart actions."
        )
    )


def test_unknown_user_cannot_approve_high_risk_action(
    client,
    override_llm_provider,
):
    cleanup_database()

    manager_headers = auth_headers("manager-123")

    task_response = client.post(
        "/tasks",
        json={
            "request": "Restart payment worker",
        },
        headers=manager_headers,
    )

    assert task_response.status_code == 200

    task_id = task_response.json()["id"]

    approval_response = client.post(
        "/approvals",
        json={
            "task_id": task_id,
            "tool_name": "service.restart",
            "risk_level": "high",
            "reason": "High-risk operation requires human approval.",
        },
        headers=manager_headers,
    )

    assert approval_response.status_code == 201

    approval_id = approval_response.json()["id"]

    unknown_headers = auth_headers("unknown-user")

    response = client.post(
        f"/approvals/{approval_id}/approve",
        headers=unknown_headers,
    )

    assert response.status_code == 403

    assert (
        response.json()["detail"]
        == (
            "User does not have permission to approve "
            "operational restart actions."
        )
    )


def test_operations_engineer_cannot_reject_high_risk_action(
    client,
    override_llm_provider,
):
    cleanup_database()

    manager_headers = auth_headers("manager-123")

    task_response = client.post(
        "/tasks",
        json={
            "request": "Restart payment worker",
        },
        headers=manager_headers,
    )

    assert task_response.status_code == 200

    task_id = task_response.json()["id"]

    approval_response = client.post(
        "/approvals",
        json={
            "task_id": task_id,
            "tool_name": "service.restart",
            "risk_level": "high",
            "reason": "High-risk operation requires human approval.",
        },
        headers=manager_headers,
    )

    assert approval_response.status_code == 201

    approval_id = approval_response.json()["id"]

    engineer_headers = auth_headers("user-123")

    response = client.post(
        f"/approvals/{approval_id}/reject",
        headers=engineer_headers,
    )

    assert response.status_code == 403

    assert (
        response.json()["detail"]
        == (
            "User does not have permission to reject "
            "operational restart actions."
        )
    )


def test_create_approval_denies_unrelated_user(
    client,
    override_llm_provider,
):
    cleanup_database()

    owner_headers = auth_headers("manager-123")

    task_response = client.post(
        "/tasks",
        json={
            "request": "Restart payment worker",
        },
        headers=owner_headers,
    )

    assert task_response.status_code == 200

    task_id = task_response.json()["id"]

    unrelated_headers = auth_headers("user-123")

    response = client.post(
        "/approvals",
        json={
            "task_id": task_id,
            "tool_name": "service.restart",
            "risk_level": "high",
            "reason": "High-risk operation requires human approval.",
        },
        headers=unrelated_headers,
    )

    assert response.status_code == 403

    assert (
        response.json()["detail"]
        == "User is not authorized to create an approval for this task."
    )


def test_create_approval_denies_completed_task(
    client,
    db_session,
    override_llm_provider,
):
    cleanup_database()

    headers = auth_headers("manager-123")

    task_response = client.post(
        "/tasks",
        json={
            "request": "Restart payment worker",
        },
        headers=headers,
    )

    assert task_response.status_code == 200

    task_id = task_response.json()["id"]

    task = db_session.get(Task, task_id)

    assert task is not None

    task.status = "completed"
    db_session.commit()

    response = client.post(
        "/approvals",
        json={
            "task_id": task_id,
            "tool_name": "service.restart",
            "risk_level": "high",
            "reason": "High-risk operation requires human approval.",
        },
        headers=headers,
    )

    assert response.status_code == 400

    assert (
        response.json()["detail"]
        == "Cannot create an approval for a completed task."
    )


def test_create_approval_denies_tool_not_selected_by_task(
    client,
    override_llm_provider,
):
    cleanup_database()

    headers = auth_headers("manager-123")

    task_response = client.post(
        "/tasks",
        json={
            "request": "Restart payment worker",
        },
        headers=headers,
    )

    assert task_response.status_code == 200

    task_id = task_response.json()["id"]

    response = client.post(
        "/approvals",
        json={
            "task_id": task_id,
            "tool_name": "database.drop",
            "risk_level": "high",
            "reason": "High-risk operation requires human approval.",
        },
        headers=headers,
    )

    assert response.status_code == 400

    assert (
        response.json()["detail"]
        == "Approval tool does not match the task's selected tool."
    )


def test_create_approval_denies_workflow_not_awaiting_approval(
    client,
    override_llm_provider,
):
    cleanup_database()

    headers = auth_headers("manager-123")

    task_response = client.post(
        "/tasks",
        json={
            "request": "Restart payment worker",
        },
        headers=headers,
    )

    assert task_response.status_code == 200

    task = task_response.json()

    assert task["status"] == "awaiting_approval"

    task_id = task["id"]

    db = SessionLocal()

    try:
        persisted_task = db.get(Task, task_id)

        assert persisted_task is not None
        assert persisted_task.workflow_thread_id is not None

        thread_id = persisted_task.workflow_thread_id

        workflow_runner = WorkflowRunner(
            llm_provider=FakeLLMProvider(
                AgentPlan(
                    reasoning_summary=(
                        "Restarting the payment worker is the "
                        "appropriate operational action."
                    ),
                    tool_call=ToolCall(
                        tool="service.restart",
                        arguments={
                            "service": "payment-worker",
                        },
                    ),
                )
            ),
            db=db,
            checkpointer=app.state.checkpointer,
        )

        workflow_state = workflow_runner.get_state(
            thread_id=thread_id,
        )

        assert (
            workflow_state.get("status")
            == AgentStatus.AWAITING_APPROVAL
        )

        workflow_runner.graph.update_state(
            {
                "configurable": {
                    "thread_id": thread_id,
                }
            },
            {
                "status": AgentStatus.EXECUTING_TOOL,
            },
        )

        updated_state = workflow_runner.get_state(
            thread_id=thread_id,
        )

        assert (
            updated_state.get("status")
            == AgentStatus.EXECUTING_TOOL
        )

    finally:
        db.close()

    response = client.post(
        "/approvals",
        json={
            "task_id": task_id,
            "tool_name": "service.restart",
            "risk_level": "high",
            "reason": "High-risk operation requires human approval.",
        },
        headers=headers,
    )

    assert response.status_code == 400

    assert (
        response.json()["detail"]
        == (
            "Cannot create an approval because the workflow "
            "is not awaiting approval."
        )
    )


def test_cannot_approve_pending_approval_with_mismatched_checkpoint_approval_id(
    client,
    override_llm_provider,
):
    cleanup_database()

    headers = auth_headers("manager-123")

    task_response = client.post(
        "/tasks",
        json={
            "request": "Restart payment worker",
        },
        headers=headers,
    )

    assert task_response.status_code == 200

    task_id = task_response.json()["id"]

    approval_response = client.post(
        "/approvals",
        json={
            "task_id": task_id,
            "tool_name": "service.restart",
            "risk_level": "high",
            "reason": "High-risk operation requires human approval.",
        },
        headers=headers,
    )

    assert approval_response.status_code == 201

    approval_id = approval_response.json()["id"]

    db = SessionLocal()

    try:
        task = db.get(Task, task_id)

        assert task is not None
        assert task.workflow_thread_id is not None

        workflow_runner = WorkflowRunner(
            llm_provider=FakeLLMProvider(
                AgentPlan(
                    reasoning_summary=(
                        "Restarting the payment worker is the "
                        "appropriate operational action."
                    ),
                    tool_call=ToolCall(
                        tool="service.restart",
                        arguments={
                            "service": "payment-worker",
                        },
                    ),
                )
            ),
            db=db,
            checkpointer=app.state.checkpointer,
        )

        workflow_state = workflow_runner.get_state(
            thread_id=task.workflow_thread_id,
        )

        assert (
            workflow_state.get("status")
            == AgentStatus.AWAITING_APPROVAL
        )

        assert workflow_state.get("approval_id") == approval_id

        workflow_runner.graph.update_state(
            {
                "configurable": {
                    "thread_id": task.workflow_thread_id,
                }
            },
            {
                "approval_id": approval_id + 999,
            },
        )

        mismatched_state = workflow_runner.get_state(
            thread_id=task.workflow_thread_id,
        )

        assert (
            mismatched_state.get("approval_id")
            == approval_id + 999
        )

    finally:
        db.close()

    response = client.post(
        f"/approvals/{approval_id}/approve",
        headers=headers,
    )

    assert response.status_code == 409

    assert response.json()["detail"] == (
        "Cannot act on the approval because the workflow "
        "approval does not match the requested approval."
    )

    db = SessionLocal()

    try:
        approval = db.get(
            ApprovalRequest,
            approval_id,
        )

        assert approval is not None
        assert approval.status == "pending"
        assert approval.decided_by is None

    finally:
        db.close()


def test_cannot_approve_pending_approval_with_mismatched_checkpoint_tool(
    client,
    override_llm_provider,
):
    cleanup_database()

    headers = auth_headers("manager-123")

    task_response = client.post(
        "/tasks",
        json={
            "request": "Restart payment worker",
        },
        headers=headers,
    )

    assert task_response.status_code == 200

    task_id = task_response.json()["id"]

    approval_response = client.post(
        "/approvals",
        json={
            "task_id": task_id,
            "tool_name": "service.restart",
            "risk_level": "high",
            "reason": "High-risk operation requires human approval.",
        },
        headers=headers,
    )

    assert approval_response.status_code == 201

    approval_id = approval_response.json()["id"]

    db = SessionLocal()

    try:
        task = db.get(Task, task_id)

        assert task is not None
        assert task.workflow_thread_id is not None

        workflow_runner = WorkflowRunner(
            llm_provider=FakeLLMProvider(
                AgentPlan(
                    reasoning_summary=(
                        "Restarting the payment worker is the "
                        "appropriate operational action."
                    ),
                    tool_call=ToolCall(
                        tool="service.restart",
                        arguments={
                            "service": "payment-worker",
                        },
                    ),
                )
            ),
            db=db,
            checkpointer=app.state.checkpointer,
        )

        workflow_state = workflow_runner.get_state(
            thread_id=task.workflow_thread_id,
        )

        assert (
            workflow_state.get("status")
            == AgentStatus.AWAITING_APPROVAL
        )

        assert (
            workflow_state.get("selected_tool")
            == "service.restart"
        )

        assert workflow_state.get("approval_id") == approval_id

        workflow_runner.graph.update_state(
            {
                "configurable": {
                    "thread_id": task.workflow_thread_id,
                }
            },
            {
                "selected_tool": "different_tool",
            },
        )

        mismatched_state = workflow_runner.get_state(
            thread_id=task.workflow_thread_id,
        )

        assert (
            mismatched_state.get("selected_tool")
            == "different_tool"
        )

    finally:
        db.close()

    response = client.post(
        f"/approvals/{approval_id}/approve",
        headers=headers,
    )

    assert response.status_code == 409

    assert response.json()["detail"] == (
        "Cannot act on the approval because the workflow "
        "tool does not match the requested approval."
    )

    db = SessionLocal()

    try:
        approval = db.get(
            ApprovalRequest,
            approval_id,
        )

        assert approval is not None
        assert approval.status == "pending"
        assert approval.decided_by is None

    finally:
        db.close()

def test_cannot_reject_pending_approval_with_mismatched_checkpoint_approval_id(
    client,
    override_llm_provider,
):
    cleanup_database()

    headers = auth_headers("manager-123")

    task_response = client.post(
        "/tasks",
        json={
            "request": "Restart payment worker",
        },
        headers=headers,
    )

    assert task_response.status_code == 200

    task_id = task_response.json()["id"]

    approval_response = client.post(
        "/approvals",
        json={
            "task_id": task_id,
            "tool_name": "service.restart",
            "risk_level": "high",
            "reason": "High-risk operation requires human approval.",
        },
        headers=headers,
    )

    assert approval_response.status_code == 201

    approval_id = approval_response.json()["id"]

    db = SessionLocal()

    try:
        task = db.get(Task, task_id)

        assert task is not None
        assert task.workflow_thread_id is not None

        workflow_runner = WorkflowRunner(
            llm_provider=FakeLLMProvider(
                AgentPlan(
                    reasoning_summary=(
                        "Restarting the payment worker is the "
                        "appropriate operational action."
                    ),
                    tool_call=ToolCall(
                        tool="service.restart",
                        arguments={
                            "service": "payment-worker",
                        },
                    ),
                )
            ),
            db=db,
            checkpointer=app.state.checkpointer,
        )

        workflow_state = workflow_runner.get_state(
            thread_id=task.workflow_thread_id,
        )

        assert (
            workflow_state.get("status")
            == AgentStatus.AWAITING_APPROVAL
        )

        assert workflow_state.get("approval_id") == approval_id

        workflow_runner.graph.update_state(
            {
                "configurable": {
                    "thread_id": task.workflow_thread_id,
                }
            },
            {
                "approval_id": approval_id + 999,
            },
        )

        mismatched_state = workflow_runner.get_state(
            thread_id=task.workflow_thread_id,
        )

        assert (
            mismatched_state.get("approval_id")
            == approval_id + 999
        )

    finally:
        db.close()

    response = client.post(
        f"/approvals/{approval_id}/reject",
        headers=headers,
    )

    assert response.status_code == 409

    assert response.json()["detail"] == (
        "Cannot act on the approval because the workflow "
        "approval does not match the requested approval."
    )

    db = SessionLocal()

    try:
        approval = db.get(
            ApprovalRequest,
            approval_id,
        )

        assert approval is not None
        assert approval.status == "pending"
        assert approval.decided_by is None

    finally:
        db.close()


def test_cannot_reject_pending_approval_with_mismatched_checkpoint_tool(
    client,
    override_llm_provider,
):
    cleanup_database()

    headers = auth_headers("manager-123")

    task_response = client.post(
        "/tasks",
        json={
            "request": "Restart payment worker",
        },
        headers=headers,
    )

    assert task_response.status_code == 200

    task_id = task_response.json()["id"]

    approval_response = client.post(
        "/approvals",
        json={
            "task_id": task_id,
            "tool_name": "service.restart",
            "risk_level": "high",
            "reason": "High-risk operation requires human approval.",
        },
        headers=headers,
    )

    assert approval_response.status_code == 201

    approval_id = approval_response.json()["id"]

    db = SessionLocal()

    try:
        task = db.get(Task, task_id)

        assert task is not None
        assert task.workflow_thread_id is not None

        workflow_runner = WorkflowRunner(
            llm_provider=FakeLLMProvider(
                AgentPlan(
                    reasoning_summary=(
                        "Restarting the payment worker is the "
                        "appropriate operational action."
                    ),
                    tool_call=ToolCall(
                        tool="service.restart",
                        arguments={
                            "service": "payment-worker",
                        },
                    ),
                )
            ),
            db=db,
            checkpointer=app.state.checkpointer,
        )

        workflow_state = workflow_runner.get_state(
            thread_id=task.workflow_thread_id,
        )

        assert (
            workflow_state.get("status")
            == AgentStatus.AWAITING_APPROVAL
        )

        assert (
            workflow_state.get("selected_tool")
            == "service.restart"
        )

        assert workflow_state.get("approval_id") == approval_id

        workflow_runner.graph.update_state(
            {
                "configurable": {
                    "thread_id": task.workflow_thread_id,
                }
            },
            {
                "selected_tool": "different_tool",
            },
        )

        mismatched_state = workflow_runner.get_state(
            thread_id=task.workflow_thread_id,
        )

        assert (
            mismatched_state.get("selected_tool")
            == "different_tool"
        )

    finally:
        db.close()

    response = client.post(
        f"/approvals/{approval_id}/reject",
        headers=headers,
    )

    assert response.status_code == 409

    assert response.json()["detail"] == (
        "Cannot act on the approval because the workflow "
        "tool does not match the requested approval."
    )

    db = SessionLocal()

    try:
        approval = db.get(
            ApprovalRequest,
            approval_id,
        )

        assert approval is not None
        assert approval.status == "pending"
        assert approval.decided_by is None

    finally:
        db.close()



def test_approve_resume_failure_leaves_approval_approved_and_task_failed(
    client,
    override_llm_provider,
    monkeypatch,
):
    cleanup_database()

    headers = auth_headers("manager-123")

    task_response = client.post(
        "/tasks",
        json={"request": "Restart payment worker"},
        headers=headers,
    )
    assert task_response.status_code == 200
    task_id = task_response.json()["id"]

    approval_response = client.post(
        "/approvals",
        json={
            "task_id": task_id,
            "tool_name": "service.restart",
            "risk_level": "high",
            "reason": "Regression test for resume failure.",
        },
        headers=headers,
    )
    assert approval_response.status_code == 201
    approval_id = approval_response.json()["id"]

    original_resume = WorkflowRunner.resume

    def fail_graph_invoke(self, *args, **kwargs):
        def failing_invoke(*invoke_args, **invoke_kwargs):
            raise RuntimeError("Simulated workflow resume failure.")

        monkeypatch.setattr(self.graph, "invoke", failing_invoke)
        return original_resume(self, *args, **kwargs)

    monkeypatch.setattr(
        WorkflowRunner,
        "resume",
        fail_graph_invoke,
    )

    with pytest.raises(
        RuntimeError,
        match="Simulated workflow resume failure.",
    ):
        client.post(
            f"/approvals/{approval_id}/approve",
            headers=headers,
        )

    db = SessionLocal()
    try:
        approval = db.get(ApprovalRequest, approval_id)
        task = db.get(Task, task_id)

        assert approval is not None
        assert approval.status == "approved"
        assert approval.decided_by == "manager-123"

        assert task is not None
        assert task.status == "failed"
    finally:
        db.close()
