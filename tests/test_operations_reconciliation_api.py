from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from app.auth_settings import AuthSettings
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


def auth_headers(user_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_token(user_id)}",
    }


def test_manager_can_view_execution_reconciliation():
    with TestClient(app) as client:
        response = client.get(
            "/operations/execution-reconciliation",
            headers=auth_headers("manager-123"),
        )

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert data["read_only"] is True


def test_admin_can_view_execution_reconciliation():
    with TestClient(app) as client:
        response = client.get(
            "/operations/execution-reconciliation",
            headers=auth_headers("admin-123"),
        )

    assert response.status_code == 200
    assert response.json()["read_only"] is True


def test_regular_user_cannot_view_execution_reconciliation():
    with TestClient(app) as client:
        response = client.get(
            "/operations/execution-reconciliation",
            headers=auth_headers("user-123"),
        )

    assert response.status_code == 403
