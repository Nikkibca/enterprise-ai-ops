from app.policy.authorization import (
    AuthorizationContext,
    build_authorization_context,
)


def test_known_engineer_has_expected_authorization_context():
    context = build_authorization_context("user-123")

    assert context == AuthorizationContext(
        user_id="user-123",
        role="operations_engineer",
        permissions=frozenset(
            {
                "knowledge.read",
                "data.read",
                "analytics.execute",
            }
        ),
    )


def test_known_manager_has_restart_permission():
    context = build_authorization_context("manager-123")

    assert context.user_id == "manager-123"
    assert context.role == "operations_manager"
    assert "operations.restart" in context.permissions


def test_unknown_user_has_empty_authorization_context():
    context = build_authorization_context("unknown-user")

    assert context.user_id == "unknown-user"
    assert context.role is None
    assert context.permissions == frozenset()