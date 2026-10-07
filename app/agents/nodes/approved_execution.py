from sqlalchemy.orm import Session

from app.agents.state import AgentState, AgentStatus
from app.approval_guard import (
    ApprovalGuardError,
    require_approved_action,
)
from app.audit.service import record_audit_event
from app.tools.factory import create_tool_registry
from app.tools.registry import ToolExecutionError


def approved_execution_node(
    state: AgentState,
    db: Session,
) -> AgentState:
    """
    Execute a previously approved high-risk tool.

    This node never decides whether approval is required.
    It only executes after the approval guard confirms authorization.
    """

    approval_id = state.get("approval_id")
    task_id = state.get("task_id")
    selected_tool = state.get("selected_tool")
    tool_arguments = state.get("tool_arguments", {})
    user_id = state.get("user_id", "unknown")

    if approval_id is None:
        return {
            "status": AgentStatus.FAILED,
            "error": "Cannot execute approved action without approval_id.",
        }

    if task_id is None:
        return {
            "status": AgentStatus.FAILED,
            "error": "Cannot execute approved action without task_id.",
        }

    if not selected_tool:
        return {
            "status": AgentStatus.FAILED,
            "error": "Cannot execute approved action without selected_tool.",
        }

    try:
        require_approved_action(
            db=db,
            approval_id=approval_id,
            task_id=task_id,
            tool_name=selected_tool,
        )

        registry = create_tool_registry()

        record_audit_event(
            db=db,
            task_id=task_id,
            event_type="tool.invoked",
            actor=user_id,
            details={
                "tool_name": selected_tool,
                "risk_level": "high",
                "approval_id": approval_id,
            },
        )

        try:
            result = registry.execute(
                selected_tool,
                tool_arguments,
            )

        except (
            ToolExecutionError,
            ValueError,
        ) as exc:
            record_audit_event(
                db=db,
                task_id=task_id,
                event_type="tool.completed",
                actor=user_id,
                details={
                    "tool_name": selected_tool,
                    "risk_level": "high",
                    "approval_id": approval_id,
                    "status": "failed",
                    "error": str(exc),
                },
            )

            return {
                "status": AgentStatus.FAILED,
                "error": str(exc),
            }

        record_audit_event(
            db=db,
            task_id=task_id,
            event_type="tool.completed",
            actor=user_id,
            details={
                "tool_name": selected_tool,
                "risk_level": "high",
                "approval_id": approval_id,
                "status": "success",
            },
        )

    except ApprovalGuardError as exc:
        return {
            "status": AgentStatus.FAILED,
            "error": str(exc),
        }

    return {
        "status": AgentStatus.EXECUTING_ACTION,
        "approval_granted": True,
        "tool_result": result,
    }