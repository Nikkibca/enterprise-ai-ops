import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApprovalRequest, AuditEvent

logger = logging.getLogger(__name__)


def get_execution_reconciliation_report(
    db: Session,
) -> list[dict]:
    """Report claimed executions without a matching completion event.

    This function is read-only. A missing completion event does not
    establish whether the external operation succeeded or failed.
    """
    claimed_approvals = db.scalars(
        select(ApprovalRequest)
        .where(ApprovalRequest.execution_claimed_at.is_not(None))
        .order_by(ApprovalRequest.id)
    ).all()

    if not claimed_approvals:
        logger.info(
            "Execution reconciliation completed: "
            "claimed=0, uncertain=0"
        )
        return []

    approval_ids = {approval.id for approval in claimed_approvals}
    task_ids = {approval.task_id for approval in claimed_approvals}

    completion_events = db.scalars(
        select(AuditEvent).where(
            AuditEvent.event_type == "tool.completed",
            AuditEvent.task_id.in_(task_ids),
        )
    ).all()

    completed_approval_ids: set[int] = set()

    for event in completion_events:
        try:
            details = json.loads(event.details or "{}")
        except (json.JSONDecodeError, TypeError):
            continue

        if not isinstance(details, dict):
            continue

        approval_id = details.get("approval_id")
        outcome = details.get("status")
        tool_name = details.get("tool_name")

        if (
            isinstance(approval_id, int)
            and not isinstance(approval_id, bool)
            and approval_id in approval_ids
            and isinstance(outcome, str)
            and outcome in {"success", "failed"}
            and isinstance(tool_name, str)
        ):
            matching_approval = next(
                (
                    approval
                    for approval in claimed_approvals
                    if approval.id == approval_id
                ),
                None,
            )

            if (
                matching_approval is not None
                and matching_approval.tool_name == tool_name
                and matching_approval.task_id == event.task_id
            ):
                completed_approval_ids.add(approval_id)


    report = []

    for approval in claimed_approvals:
        if approval.id in completed_approval_ids:
            continue

        report.append(
            {
                "approval_id": approval.id,
                "task_id": approval.task_id,
                "tool_name": approval.tool_name,
                "claimed_at": approval.execution_claimed_at.isoformat(),
                "claimed_by": approval.execution_claimed_by,
                "outcome": "uncertain",
                "requires_manual_review": True,
            }
        )

    return report
