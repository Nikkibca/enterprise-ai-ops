from datetime import datetime, timedelta, timezone

import jwt

from fastapi.testclient import TestClient

from app.auth_settings import AuthSettings
from app.dependencies import get_checkpointer, get_llm_provider
from app.main import app


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


class FakeLLMProvider:
    pass


class FakeCheckpointer:
    pass


def test_create_task_endpoint_wires_workflow_dependencies(
    monkeypatch,
):
    fake_llm_provider = FakeLLMProvider()
    fake_checkpointer = FakeCheckpointer()

    app.dependency_overrides[get_llm_provider] = (
        lambda: fake_llm_provider
    )
    app.dependency_overrides[get_checkpointer] = (
        lambda: fake_checkpointer
    )

    captured = {}

    class FakeWorkflowRunner:
        def __init__(
            self,
            llm_provider,
            db,
            checkpointer,
        ):
            captured["llm_provider"] = llm_provider
            captured["db"] = db
            captured["checkpointer"] = checkpointer

    def fake_start_task_workflow(
        db,
        task,
        workflow_runner,
    ):
        captured["workflow_runner"] = workflow_runner

    monkeypatch.setattr(
        "app.api.WorkflowRunner",
        FakeWorkflowRunner,
    )
    monkeypatch.setattr(
        "app.api.start_task_workflow",
        fake_start_task_workflow,
    )

    client = TestClient(app)

    try:
        response = client.post(
            "/tasks",
            json={
                "request": "Investigate payment failures.",
            },
            headers={
                "Authorization": (
                    f"Bearer {create_token('user-123')}"
                ),
            },
        )

        assert response.status_code == 200

        assert (
            captured["llm_provider"]
            is fake_llm_provider
        )

        assert (
            captured["checkpointer"]
            is fake_checkpointer
        )

        assert (
            captured["workflow_runner"].__class__
            is FakeWorkflowRunner
        )

        data = response.json()

        assert data["user_id"] == "user-123"
        assert (
            data["request"]
            == "Investigate payment failures."
        )

    finally:
        app.dependency_overrides.clear()


def test_create_task_requires_authentication():
    client = TestClient(app)

    response = client.post(
        "/tasks",
        json={
            "request": "Investigate payment failures.",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Authentication required."
    )


def test_client_cannot_supply_user_id_in_request_body(
    monkeypatch,
):
    fake_llm_provider = FakeLLMProvider()
    fake_checkpointer = FakeCheckpointer()

    app.dependency_overrides[get_llm_provider] = (
        lambda: fake_llm_provider
    )
    app.dependency_overrides[get_checkpointer] = (
        lambda: fake_checkpointer
    )

    class FakeWorkflowRunner:
        def __init__(
            self,
            llm_provider,
            db,
            checkpointer,
        ):
            pass

    def fake_start_task_workflow(
        db,
        task,
        workflow_runner,
    ):
        pass

    monkeypatch.setattr(
        "app.api.WorkflowRunner",
        FakeWorkflowRunner,
    )
    monkeypatch.setattr(
        "app.api.start_task_workflow",
        fake_start_task_workflow,
    )

    client = TestClient(app)

    try:
        response = client.post(
            "/tasks",
            json={
                "user_id": "manager-123",
                "request": "Investigate payment failures.",
            },
            headers={
                "Authorization": (
                    f"Bearer {create_token('user-123')}"
                ),
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["user_id"] == "user-123"

    finally:
        app.dependency_overrides.clear()

def test_task_owner_can_view_own_task(
    monkeypatch,
):
    fake_llm_provider = FakeLLMProvider()
    fake_checkpointer = FakeCheckpointer()

    app.dependency_overrides[get_llm_provider] = (
        lambda: fake_llm_provider
    )
    app.dependency_overrides[get_checkpointer] = (
        lambda: fake_checkpointer
    )

    class FakeWorkflowRunner:
        def __init__(
            self,
            llm_provider,
            db,
            checkpointer,
        ):
            pass

    def fake_start_task_workflow(
        db,
        task,
        workflow_runner,
    ):
        pass

    monkeypatch.setattr(
        "app.api.WorkflowRunner",
        FakeWorkflowRunner,
    )
    monkeypatch.setattr(
        "app.api.start_task_workflow",
        fake_start_task_workflow,
    )

    client = TestClient(app)

    try:
        create_response = client.post(
            "/tasks",
            json={
                "request": "Investigate payment failures.",
            },
            headers={
                "Authorization": (
                    f"Bearer {create_token('user-123')}"
                ),
            },
        )

        assert create_response.status_code == 200

        task_id = create_response.json()["id"]

        response = client.get(
            f"/tasks/{task_id}",
            headers={
                "Authorization": (
                    f"Bearer {create_token('user-123')}"
                ),
            },
        )

        assert response.status_code == 200
        assert response.json()["user_id"] == "user-123"

    finally:
        app.dependency_overrides.clear()


def test_unknown_user_cannot_view_another_users_task(
    monkeypatch,
):
    fake_llm_provider = FakeLLMProvider()
    fake_checkpointer = FakeCheckpointer()

    app.dependency_overrides[get_llm_provider] = (
        lambda: fake_llm_provider
    )
    app.dependency_overrides[get_checkpointer] = (
        lambda: fake_checkpointer
    )

    class FakeWorkflowRunner:
        def __init__(
            self,
            llm_provider,
            db,
            checkpointer,
        ):
            pass

    def fake_start_task_workflow(
        db,
        task,
        workflow_runner,
    ):
        pass

    monkeypatch.setattr(
        "app.api.WorkflowRunner",
        FakeWorkflowRunner,
    )
    monkeypatch.setattr(
        "app.api.start_task_workflow",
        fake_start_task_workflow,
    )

    client = TestClient(app)

    try:
        create_response = client.post(
            "/tasks",
            json={
                "request": "Investigate payment failures.",
            },
            headers={
                "Authorization": (
                    f"Bearer {create_token('user-123')}"
                ),
            },
        )

        assert create_response.status_code == 200

        task_id = create_response.json()["id"]

        response = client.get(
            f"/tasks/{task_id}",
            headers={
                "Authorization": (
                    f"Bearer {create_token('unknown-user')}"
                ),
            },
        )

        assert response.status_code == 403
        assert response.json()["detail"] == (
            "User is not authorized to view this task."
        )

    finally:
        app.dependency_overrides.clear()


def test_operations_manager_can_view_another_users_task(
    monkeypatch,
):
    fake_llm_provider = FakeLLMProvider()
    fake_checkpointer = FakeCheckpointer()

    app.dependency_overrides[get_llm_provider] = (
        lambda: fake_llm_provider
    )
    app.dependency_overrides[get_checkpointer] = (
        lambda: fake_checkpointer
    )

    class FakeWorkflowRunner:
        def __init__(
            self,
            llm_provider,
            db,
            checkpointer,
        ):
            pass

    def fake_start_task_workflow(
        db,
        task,
        workflow_runner,
    ):
        pass

    monkeypatch.setattr(
        "app.api.WorkflowRunner",
        FakeWorkflowRunner,
    )
    monkeypatch.setattr(
        "app.api.start_task_workflow",
        fake_start_task_workflow,
    )

    client = TestClient(app)

    try:
        create_response = client.post(
            "/tasks",
            json={
                "request": "Investigate payment failures.",
            },
            headers={
                "Authorization": (
                    f"Bearer {create_token('user-123')}"
                ),
            },
        )

        assert create_response.status_code == 200

        task_id = create_response.json()["id"]

        response = client.get(
            f"/tasks/{task_id}",
            headers={
                "Authorization": (
                    f"Bearer {create_token('manager-123')}"
                ),
            },
        )

        assert response.status_code == 200
        assert response.json()["user_id"] == "user-123"

    finally:
        app.dependency_overrides.clear()        