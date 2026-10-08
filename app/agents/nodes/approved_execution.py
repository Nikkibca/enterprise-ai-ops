from sqlalchemy.orm import Session

from app.agents.state import AgentState, AgentStatus
from app.approval_guard import (
    ApprovalGuardError,
    require_approved_action,
)

from app.approval_service import (
    claim_approved_execution,
    get_approval,
)

from app.audit.service import record_audit_event
from app.approval_service import get_approval
from app.models import ApprovalStatus
from app.tools.factory import create_tool_registry
from app.tools.registry import ToolExecutionError


def approved_execution_node(
    state: AgentState,
    db: Session,
) -> AgentState:
    """
    Execute a previously approved high-risk tool.

    The persisted approval record is the authoritative source for
    the approver identity. Checkpoint state is not trusted as the
    authorization source.
    """

    approval_id = state.get("approval_id")
    task_id = state.get("task_id")
    selected_tool = state.get("selected_tool")
    tool_arguments = state.get("tool_arguments", {})

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

        approval = get_approval(
            db=db,
            approval_id=approval_id,
        )

        if approval.status != ApprovalStatus.APPROVED.value:
            return {
                "status": AgentStatus.FAILED,
                "error": (
                    "Tool execution requires an approved approval request."
                ),
            }

        approver = approval.decided_by

        if not isinstance(approver, str) or not approver.strip():
            return {
                "status": AgentStatus.FAILED,
                "error": (
                    "Approved action is missing the identity of the approver."
                ),
            }

        approver = approver.strip()

        claimed = claim_approved_execution(
            db=db,
            approval_id=approval_id,
            executor=approver,
        )

        if not claimed:
            return {
                "status": AgentStatus.FAILED,
                "error": (
                    "Approved action has already been claimed for execution."
                ),
            }

        try:
            record_audit_event(
                db=db,
                task_id=task_id,
                event_type="tool.invoked",
                actor=approver,
                details={
                    "tool_name": selected_tool,
                    "risk_level": "high",
                    "approval_id": approval_id,
                    "approved_by": approver,
                },
            )
        except Exception as exc:
            db.rollback()

            return {
                "status": AgentStatus.FAILED,
                "error": str(exc),
            }    

        registry = create_tool_registry()

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
                actor=approver,
                details={
                    "tool_name": selected_tool,
                    "risk_level": "high",
                    "approval_id": approval_id,
                    "approved_by": approver,
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
            actor=approver,
            details={
                "tool_name": selected_tool,
                "risk_level": "high",
                "approval_id": approval_id,
                "approved_by": approver,
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
        "approval_decided_by": approver,
        "tool_result": result,
    }