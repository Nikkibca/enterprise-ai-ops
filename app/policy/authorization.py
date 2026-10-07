from dataclasses import dataclass

from app.policy.permissions import (
    get_user_permissions,
    get_user_role,
)


@dataclass(frozen=True)
class AuthorizationContext:
    user_id: str
    role: str | None
    permissions: frozenset[str]


def build_authorization_context(
    user_id: str,
) -> AuthorizationContext:
    role = get_user_role(user_id)
    permissions = get_user_permissions(user_id)

    return AuthorizationContext(
        user_id=user_id,
        role=role,
        permissions=frozenset(permissions),
    )