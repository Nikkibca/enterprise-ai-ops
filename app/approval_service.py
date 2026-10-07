from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.audit.service import record_audit_event
from app.models import ApprovalRequest, ApprovalStatus


class ApprovalNotFoundError(Exception):
    pass


class InvalidApprovalStateError(Exception):
    pass


def create_approval(
    db: Session,
    task_id: int,
    tool_name: str,
    risk_level: str,
    requested_by: str,
    reason: str,
) -> ApprovalRequest:
    approval = ApprovalRequest(
        task_id=task_id,
        tool_name=tool_name,
        risk_level=risk_level,
        requested_by=requested_by,
        reason=reason,
        status=ApprovalStatus.PENDING.value,
        requested_at=datetime.now(timezone.utc),
    )

    db.add(approval)
    db.flush()

    record_audit_event(
        db=db,
        task_id=task_id,
        event_type="approval.requested",
        actor=requested_by,
        details={
            "approval_id": approval.id,
            "tool_name": tool_name,
            "risk_level": risk_level,
            "reason": reason,
        },
        commit=False,
    )

    db.commit()
    db.refresh(approval)

    return approval


def get_approval(
    db: Session,
    approval_id: int,
) -> ApprovalRequest:
    approval = db.get(ApprovalRequest, approval_id)

    if approval is None:
        raise ApprovalNotFoundError(
            f"Approval request not found: {approval_id}"
        )

    return approval


def approve_request(
    db: Session,
    approval_id: int,
    decided_by: str,
) -> ApprovalRequest:
    approval = get_approval(db, approval_id)

    if approval.status != ApprovalStatus.PENDING.value:
        raise InvalidApprovalStateError(
            "Only pending approval requests can be approved."
        )

    approval.status = ApprovalStatus.APPROVED.value
    approval.decided_by = decided_by
    approval.decided_at = datetime.now(timezone.utc)

    record_audit_event(
        db=db,
        task_id=approval.task_id,
        event_type="approval.granted",
        actor=decided_by,
        details={
            "approval_id": approval.id,
            "tool_name": approval.tool_name,
        },
        commit=False,
    )

    db.commit()
    db.refresh(approval)

    return approval


def reject_request(
    db: Session,
    approval_id: int,
    decided_by: str,
) -> ApprovalRequest:
    approval = get_approval(db, approval_id)

    if approval.status != ApprovalStatus.PENDING.value:
        raise InvalidApprovalStateError(
            "Only pending approval requests can be rejected."
        )

    approval.status = ApprovalStatus.REJECTED.value
    approval.decided_by = decided_by
    approval.decided_at = datetime.now(timezone.utc)

    record_audit_event(
        db=db,
        task_id=approval.task_id,
        event_type="approval.rejected",
        actor=decided_by,
        details={
            "approval_id": approval.id,
            "tool_name": approval.tool_name,
        },
        commit=False,
    )

    db.commit()
    db.refresh(approval)

    return approval