from app.policy.engine import PolicyDecision, evaluate_tool
from app.policy.permissions import get_tool_risk
from app.policy.risk import RiskLevel


def test_knowledge_search_is_low_risk():
    assert get_tool_risk("knowledge.search") == RiskLevel.LOW


def test_sql_read_is_low_risk():
    assert get_tool_risk("sql.read") == RiskLevel.LOW


def test_python_analysis_is_medium_risk():
    assert get_tool_risk("python.analysis") == RiskLevel.MEDIUM


def test_service_restart_is_high_risk():
    assert get_tool_risk("service.restart") == RiskLevel.HIGH


def test_unknown_tool_is_critical():
    assert get_tool_risk("shell.execute") == RiskLevel.CRITICAL


def test_low_risk_tool_is_allowed():
    result = evaluate_tool(
        tool_name="sql.read",
        user_id="user-123",
    )

    assert result.decision == PolicyDecision.ALLOW
    assert result.risk_level == RiskLevel.LOW


def test_medium_risk_tool_is_allowed_with_audit():
    result = evaluate_tool(
        tool_name="python.analysis",
        user_id="user-123",
    )

    assert result.decision == PolicyDecision.ALLOW
    assert result.risk_level == RiskLevel.MEDIUM


def test_high_risk_tool_requires_approval():
    result = evaluate_tool(
        tool_name="service.restart",
        user_id="manager-123",
    )

    assert result.decision == PolicyDecision.APPROVAL_REQUIRED
    assert result.risk_level == RiskLevel.HIGH


def test_critical_tool_is_denied():
    result = evaluate_tool(
        tool_name="shell.execute",
        user_id="user-123",
    )

    assert result.decision == PolicyDecision.DENY
    assert result.risk_level == RiskLevel.CRITICAL


def test_tool_without_required_permission_is_denied():
    result = evaluate_tool(
        tool_name="sql.read",
        user_id="unknown-user",
    )

    assert result.decision == PolicyDecision.DENY
    assert result.risk_level == RiskLevel.LOW
    assert "data.read" in result.reason


def test_tool_with_required_permission_remains_allowed():
    result = evaluate_tool(
        tool_name="sql.read",
        user_id="user-123",
    )

    assert result.decision == PolicyDecision.ALLOW
    assert result.risk_level == RiskLevel.LOW

def test_policy_result_contains_authorization_metadata():
    result = evaluate_tool(
        tool_name="sql.read",
        user_id="user-123",
    )

    assert result.user_id == "user-123"
    assert result.role == "operations_engineer"
    assert result.required_permission == "data.read"


def test_denied_policy_result_contains_authorization_metadata():
    result = evaluate_tool(
        tool_name="sql.read",
        user_id="unknown-user",
    )

    assert result.decision == PolicyDecision.DENY
    assert result.user_id == "unknown-user"
    assert result.role is None
    assert result.required_permission == "data.read"


def test_high_risk_policy_result_contains_authorization_metadata():
    result = evaluate_tool(
        tool_name="service.restart",
        user_id="manager-123",
    )

    assert result.decision == PolicyDecision.APPROVAL_REQUIRED
    assert result.user_id == "manager-123"
    assert result.role == "operations_manager"
    assert result.required_permission == "operations.restart"    