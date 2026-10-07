from sqlalchemy.orm import Session

from app.agents.schemas import ToolCall
from app.agents.state import AgentState, AgentStatus
from app.agents.tool_validation import (
    ToolValidationError,
    validate_tool_call,
)
from app.approval_service import create_approval
from app.audit.service import record_audit_event
from app.policy.engine import (
    PolicyDecision,
    evaluate_tool,
)
from app.tools.factory import create_tool_registry
from app.tools.registry import ToolExecutionError


def tool_execution_node(
    state: AgentState,
    db: Session | None = None,
) -> AgentState:
    selected_tool = state.get("selected_tool")

    tool_call = ToolCall(
        tool=selected_tool or "",
        arguments=state.get("tool_arguments", {}),
    )

    registry = create_tool_registry()

    try:
        validate_tool_call(
            tool_call,
            registry,
        )

        policy_result = evaluate_tool(
            tool_name=tool_call.tool,
            user_id=state.get("user_id", "unknown"),
        )

        # Record the policy decision when a database is available.
        if db is not None and state.get("task_id") is not None:
            record_audit_event(
                db=db,
                task_id=state["task_id"],
                event_type="policy.checked",
                actor=policy_result.user_id,
                details={
                    "tool_name": tool_call.tool,
                    "decision": policy_result.decision,
                    "risk_level": policy_result.risk_level.value,
                    "reason": policy_result.reason,
                    "role": policy_result.role,
                    "required_permission": (
                        policy_result.required_permission
                    ),
                },
            )

        # Critical-risk operations are denied.
        if policy_result.decision == PolicyDecision.DENY:
            return {
                "status": AgentStatus.FAILED,
                "risk_level": policy_result.risk_level.value,
                "approval_required": False,
                "error": policy_result.reason,
            }

        # High-risk operations require human approval.
        if policy_result.decision == PolicyDecision.APPROVAL_REQUIRED:
            task_id = state.get("task_id")

            if db is None:
                return {
                    "status": AgentStatus.AWAITING_APPROVAL,
                    "risk_level": policy_result.risk_level.value,
                    "approval_required": True,
                    "approval_granted": False,
                    "error": policy_result.reason,
                }

            if task_id is None:
                return {
                    "status": AgentStatus.FAILED,
                    "risk_level": policy_result.risk_level.value,
                    "approval_required": True,
                    "error": (
                        "Cannot create approval request without a task_id."
                    ),
                }

            approval = create_approval(
                db=db,
                task_id=task_id,
                tool_name=tool_call.tool,
                risk_level=policy_result.risk_level.value,
                requested_by=state.get("user_id", "unknown"),
                reason=policy_result.reason,
            )

            return {
                "status": AgentStatus.AWAITING_APPROVAL,
                "risk_level": policy_result.risk_level.value,
                "approval_required": True,
                "approval_granted": False,
                "approval_id": approval.id,
                "error": policy_result.reason,
            }

        # Low/medium-risk tools can execute immediately.

        if db is not None and state.get("task_id") is not None:
            record_audit_event(
                db=db,
                task_id=state["task_id"],
                event_type="tool.invoked",
                actor=policy_result.user_id,
                details={
                    "tool_name": tool_call.tool,
                    "risk_level": policy_result.risk_level.value,
                    "role": policy_result.role,
                },
            )

        result = registry.execute(
            tool_call.tool,
            tool_call.arguments,
        )

        if db is not None and state.get("task_id") is not None:
            record_audit_event(
                db=db,
                task_id=state["task_id"],
                event_type="tool.completed",
                actor=policy_result.user_id,
                details={
                    "tool_name": tool_call.tool,
                    "risk_level": policy_result.risk_level.value,
                    "role": policy_result.role,
                    "status": "success",
                },
            )

    except (
        ToolValidationError,
        ToolExecutionError,
        ValueError,
    ) as exc:
        return {
            "status": AgentStatus.FAILED,
            "error": str(exc),
        }

    return {
        "status": AgentStatus.EXECUTING_TOOL,
        "risk_level": policy_result.risk_level.value,
        "approval_required": False,
        "approval_granted": False,
        "tool_result": result,
    }