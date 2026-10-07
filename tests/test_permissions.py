from app.policy.permissions import (
    get_tool_permission,
    has_permission,
)


def test_get_tool_permission_for_registered_tool():
    assert (
        get_tool_permission("sql.read")
        == "data.read"
    )


def test_get_tool_permission_for_python_analysis():
    assert (
        get_tool_permission("python.analysis")
        == "analytics.execute"
    )


def test_unknown_tool_has_no_permission():
    assert get_tool_permission("shell.execute") is None


def test_user_with_required_permission_is_allowed():
    assert has_permission(
        user_permissions={"data.read"},
        required_permission="data.read",
    ) is True


def test_user_without_required_permission_is_denied():
    assert has_permission(
        user_permissions={"knowledge.read"},
        required_permission="data.read",
    ) is False

def test_operations_engineer_has_expected_permissions():
    from app.policy.permissions import get_user_permissions

    permissions = get_user_permissions("user-123")

    assert permissions == {
        "knowledge.read",
        "data.read",
        "analytics.execute",
    }


def test_operations_manager_can_restart_services():
    from app.policy.permissions import get_user_permissions

    permissions = get_user_permissions("manager-123")

    assert "operations.restart" in permissions


def test_unknown_user_has_no_permissions():
    from app.policy.permissions import get_user_permissions

    assert get_user_permissions("unknown-user") == set()
