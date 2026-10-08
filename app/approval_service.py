from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import record_audit_event
from app.models import ApprovalRequest, ApprovalStatus


class ApprovalNotFoundError(Exception):
    pass


class InvalidApprovalStateError(Exception):
    pass

def claim_approved_execution(
    db: Session,
    *,
    approval_id: int,
    executor: str,
) -> bool:
    """
    Atomically claim an approved action for execution.

    Exactly one concurrent caller can successfully claim the
    approval. The claim is committed before the external tool
    is invoked.
    """

    executor = executor.strip()

    if not executor:
        raise ValueError(
            "Execution claimant identity cannot be empty."
        )

    now = datetime.now(timezone.utc)

    result = db.execute(
        update(ApprovalRequest)
        .where(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.status
            == ApprovalStatus.APPROVED.value,
            ApprovalRequest.execution_claimed_at.is_(None),
        )
        .values(
            execution_claimed_at=now,
            execution_claimed_by=executor,
        )
    )

    if result.rowcount != 1:
        db.rollback()
        return False

    db.commit()

    return True



def create_approval(
    db: Session,
    task_id: int,
    tool_name: str,
    risk_level: str,
    requested_by: str,
    reason: str,
) -> ApprovalRequest:
    existing = db.execute(
        select(ApprovalRequest)
        .where(
            ApprovalRequest.task_id == task_id,
            ApprovalRequest.tool_name == tool_name,
            ApprovalRequest.status == ApprovalStatus.PENDING.value,
        )
        .order_by(ApprovalRequest.id)
    ).scalar_one_or_none()

    if existing is not None:
        return existing

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

    try:
        db.flush()
    except IntegrityError:
        # Another transaction may have created the same pending approval
        # between our SELECT and INSERT. The PostgreSQL partial unique
        # index makes that race safe at the database level.
        db.rollback()

        existing = db.execute(
            select(ApprovalRequest)
            .where(
                ApprovalRequest.task_id == task_id,
                ApprovalRequest.tool_name == tool_name,
                ApprovalRequest.status == ApprovalStatus.PENDING.value,
            )
            .order_by(ApprovalRequest.id)
        ).scalar_one_or_none()

        if existing is not None:
            return existing

        raise

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


def _transition_approval(
    db: Session,
    approval_id: int,
    decided_by: str,
    target_status: str,
    event_type: str,
    error_message: str,
) -> ApprovalRequest:
    decided_at = datetime.now(timezone.utc)

    result = db.execute(
        update(ApprovalRequest)
        .where(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.status == ApprovalStatus.PENDING.value,
        )
        .values(
            status=target_status,
            decided_by=decided_by,
            decided_at=decided_at,
        )
    )

    if result.rowcount != 1:
        approval = db.get(ApprovalRequest, approval_id)

        if approval is None:
            raise ApprovalNotFoundError(
                f"Approval request not found: {approval_id}"
            )

        raise InvalidApprovalStateError(error_message)

    approval = db.get(ApprovalRequest, approval_id)

    if approval is None:
        db.rollback()
        raise ApprovalNotFoundError(
            f"Approval request not found: {approval_id}"
        )

    record_audit_event(
        db=db,
        task_id=approval.task_id,
        event_type=event_type,
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


def approve_request(
    db: Session,
    approval_id: int,
    decided_by: str,
) -> ApprovalRequest:
    return _transition_approval(
        db=db,
        approval_id=approval_id,
        decided_by=decided_by,
        target_status=ApprovalStatus.APPROVED.value,
        event_type="approval.granted",
        error_message=(
            "Only pending approval requests can be approved."
        ),
    )


def reject_request(
    db: Session,
    approval_id: int,
    decided_by: str,
) -> ApprovalRequest:
    return _transition_approval(
        db=db,
        approval_id=approval_id,
        decided_by=decided_by,
        target_status=ApprovalStatus.REJECTED.value,
        event_type="approval.rejected",
        error_message=(
            "Only pending approval requests can be rejected."
        ),
    )