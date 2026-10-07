from app.policy.risk import RiskLevel
from app.tools.factory import create_tool_registry


ROLE_PERMISSIONS: dict[str, set[str]] = {
    "operations_engineer": {
        "knowledge.read",
        "data.read",
        "analytics.execute",
    },
    "operations_manager": {
        "knowledge.read",
        "data.read",
        "analytics.execute",
        "operations.restart",
    },
    "platform_admin": {
        "knowledge.read",
        "data.read",
        "analytics.execute",
        "operations.restart",
    },
}


USER_ROLES: dict[str, str] = {
    "user-123": "operations_engineer",
    "manager-123": "operations_manager",
    "admin-123": "platform_admin",
}


def get_tool_risk(tool_name: str) -> RiskLevel:
    registry = create_tool_registry()

    if not registry.is_registered(tool_name):
        return RiskLevel.CRITICAL

    tool = registry.get(tool_name)

    return RiskLevel(tool.risk_level)


def get_tool_permission(
    tool_name: str,
) -> str | None:
    registry = create_tool_registry()

    if not registry.is_registered(tool_name):
        return None

    tool = registry.get(tool_name)

    return tool.required_permission


def get_user_role(user_id: str) -> str | None:
    return USER_ROLES.get(user_id)


def get_user_permissions(
    user_id: str,
) -> set[str]:
    role = get_user_role(user_id)

    if role is None:
        return set()

    return ROLE_PERMISSIONS.get(
        role,
        set(),
    ).copy()


def has_permission(
    user_permissions: set[str],
    required_permission: str | None,
) -> bool:
    if required_permission is None:
        return False

    return required_permission in user_permissions