from sqlalchemy.orm import Session

from app.approval_service import (
    ApprovalNotFoundError,
    get_approval,
)
from app.models import ApprovalStatus


class ApprovalGuardError(Exception):
    pass


def require_approved_action(
    db: Session,
    *,
    approval_id: int,
    task_id: int,
    tool_name: str,
) -> None:
    """
    Verify that a specific tool execution is authorized by
    an approved human approval request.

    Raises ApprovalGuardError if execution is not authorized.
    """

    try:
        approval = get_approval(
            db=db,
            approval_id=approval_id,
        )
    except ApprovalNotFoundError as exc:
        raise ApprovalGuardError(str(exc)) from exc

    if approval.task_id != task_id:
        raise ApprovalGuardError(
            "Approval request does not belong to this task."
        )

    if approval.tool_name != tool_name:
        raise ApprovalGuardError(
            "Approval request does not authorize this tool."
        )

    if approval.status != ApprovalStatus.APPROVED.value:
        raise ApprovalGuardError(
            "Tool execution requires an approved approval request."
        )