from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth_settings import AuthSettings
from app.authentication import get_current_principal


def create_test_app() -> FastAPI:
    app = FastAPI()

    @app.get("/me")
    def get_me(principal=Depends(get_current_principal)):
        return {
            "user_id": principal.user_id,
        }

    return app


def create_token(
    user_id: str,
    *,
    expires_delta: timedelta = timedelta(minutes=30),
    issuer: str | None = None,
    audience: str | None = None,
) -> str:
    settings = AuthSettings()

    now = datetime.now(timezone.utc)

    return jwt.encode(
        {
            "sub": user_id,
            "iss": issuer or settings.jwt_issuer,
            "aud": audience or settings.jwt_audience,
            "iat": now,
            "exp": now + expires_delta,
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def test_jwt_authenticated_principal_is_created():
    client = TestClient(create_test_app())

    token = create_token("user-123")

    response = client.get(
        "/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "user-123",
    }


def test_missing_token_is_rejected():
    client = TestClient(create_test_app())

    response = client.get("/me")

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Authentication required."
    )


def test_invalid_jwt_is_rejected():
    client = TestClient(create_test_app())

    response = client.get(
        "/me",
        headers={
            "Authorization": "Bearer definitely-not-a-valid-token",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid authentication token."
    )


def test_jwt_without_subject_is_rejected():
    settings = AuthSettings()
    now = datetime.now(timezone.utc)

    token = jwt.encode(
        {
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": now + timedelta(minutes=30),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    client = TestClient(create_test_app())

    response = client.get(
        "/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Authentication token does not contain a valid subject."
    )


def test_jwt_with_wrong_secret_is_rejected():
    settings = AuthSettings()
    now = datetime.now(timezone.utc)

    token = jwt.encode(
        {
            "sub": "admin-123",
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": now + timedelta(minutes=30),
        },
        "wrong-secret-for-jwt-test-32-bytes!",
        algorithm="HS256",
    )

    client = TestClient(create_test_app())

    response = client.get(
        "/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid authentication token."
    )


def test_non_bearer_authentication_is_rejected():
    client = TestClient(create_test_app())

    response = client.get(
        "/me",
        headers={
            "Authorization": "Basic abc123",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Authentication required."
    )


def test_bearer_token_with_blank_subject_is_rejected():
    settings = AuthSettings()
    now = datetime.now(timezone.utc)

    token = jwt.encode(
        {
            "sub": "   ",
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": now + timedelta(minutes=30),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    client = TestClient(create_test_app())

    response = client.get(
        "/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Authentication token does not contain a valid subject."
    )


def test_jwt_subject_is_used_as_authenticated_user():
    client = TestClient(create_test_app())

    token = create_token("manager-123")

    response = client.get(
        "/me",
        headers={
            "Authorization": f"Bearer {token}",
            "X-User-ID": "admin-123",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "manager-123",
    }


def test_expired_jwt_is_rejected():
    client = TestClient(create_test_app())

    token = create_token(
        "user-123",
        expires_delta=timedelta(seconds=-1),
    )

    response = client.get(
        "/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid authentication token."
    )


def test_wrong_issuer_is_rejected():
    client = TestClient(create_test_app())

    token = create_token(
        "user-123",
        issuer="wrong-issuer",
    )

    response = client.get(
        "/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid authentication token."
    )


def test_wrong_audience_is_rejected():
    client = TestClient(create_test_app())

    token = create_token(
        "user-123",
        audience="wrong-audience",
    )

    response = client.get(
        "/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid authentication token."
    )