from dataclasses import dataclass

from app.policy.authorization import build_authorization_context
from app.policy.permissions import (
    get_tool_permission,
    get_tool_risk,
    has_permission,
)
from app.policy.risk import RiskLevel


class PolicyDecision(str):
    ALLOW = "allow"
    APPROVAL_REQUIRED = "approval_required"
    DENY = "deny"


@dataclass(frozen=True)
class PolicyResult:
    decision: str
    risk_level: RiskLevel
    reason: str
    user_id: str
    role: str | None
    required_permission: str | None


def evaluate_tool(
    tool_name: str,
    user_id: str,
) -> PolicyResult:
    authorization = build_authorization_context(user_id)

    risk_level = get_tool_risk(tool_name)
    required_permission = get_tool_permission(tool_name)

    common = {
        "user_id": authorization.user_id,
        "role": authorization.role,
        "required_permission": required_permission,
    }

    # Unknown tools are treated as critical and denied.
    if risk_level == RiskLevel.CRITICAL:
        return PolicyResult(
            decision=PolicyDecision.DENY,
            risk_level=risk_level,
            reason="Critical-risk operation is not permitted.",
            **common,
        )

    # Authorization is resolved centrally from the user's identity.
    if not has_permission(
        set(authorization.permissions),
        required_permission,
    ):
        return PolicyResult(
            decision=PolicyDecision.DENY,
            risk_level=risk_level,
            reason=(
                f"User lacks required permission: "
                f"{required_permission}"
            ),
            **common,
        )

    if risk_level == RiskLevel.LOW:
        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            risk_level=risk_level,
            reason="Low-risk tool is allowed.",
            **common,
        )

    if risk_level == RiskLevel.MEDIUM:
        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            risk_level=risk_level,
            reason="Medium-risk tool is allowed with audit logging.",
            **common,
        )

    if risk_level == RiskLevel.HIGH:
        return PolicyResult(
            decision=PolicyDecision.APPROVAL_REQUIRED,
            risk_level=risk_level,
            reason="High-risk operation requires human approval.",
            **common,
        )

    return PolicyResult(
        decision=PolicyDecision.DENY,
        risk_level=risk_level,
        reason="Critical-risk operation is not permitted.",
        **common,
    )