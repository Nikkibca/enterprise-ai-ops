from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth_settings import AuthSettings


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user_id: str


bearer_scheme = HTTPBearer(auto_error=False)


def _authenticate_jwt(
    credentials: HTTPAuthorizationCredentials,
) -> AuthenticatedPrincipal:
    settings = AuthSettings()

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        ) from exc

    user_id = payload.get("sub")

    if not isinstance(user_id, str) or not user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token does not contain a valid subject.",
        )

    return AuthenticatedPrincipal(
        user_id=user_id.strip(),
    )


def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> AuthenticatedPrincipal:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication required.",
        )

    return _authenticate_jwt(credentials)