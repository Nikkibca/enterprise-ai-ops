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
    commit: bool = True,
) -> bool:
    """
    Atomically claim an approved request for execution.

    Only one executor can claim an approval. If commit=False, the caller
    controls the transaction.
    """
    executor = executor.strip()

    if not executor:
        raise ValueError("Execution claimant identity cannot be empty.")

    now = datetime.now(timezone.utc)

    result = db.execute(
        update(ApprovalRequest)
        .where(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.status == ApprovalStatus.APPROVED.value,
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

    if commit:
        db.commit()

    return True


def _get_matching_pending_approval(
    db: Session,
    *,
    task_id: int,
    tool_name: str,
    tool_arguments: dict,
) -> ApprovalRequest | None:
    """
    Return an existing pending approval only when its argument snapshot
    matches the newly requested arguments exactly.
    """
    existing = db.execute(
        select(ApprovalRequest)
        .where(
            ApprovalRequest.task_id == task_id,
            ApprovalRequest.tool_name == tool_name,
            ApprovalRequest.status == ApprovalStatus.PENDING.value,
        )
        .order_by(ApprovalRequest.id)
    ).scalar_one_or_none()

    if existing is None:
        return None

    if existing.tool_arguments != tool_arguments:
        raise InvalidApprovalStateError(
            "A pending approval already exists for this task and tool "
            "with different arguments."
        )

    return existing


def create_approval(
    db: Session,
    task_id: int,
    tool_name: str,
    risk_level: str,
    requested_by: str,
    reason: str,
    *,
    tool_arguments: dict,
) -> ApprovalRequest:
    """
    Create an approval request and persist the exact tool-argument
    snapshot that the human is being asked to approve.

    Repeated requests may reuse an existing pending approval only if the
    tool arguments match the saved snapshot.
    """
    if not isinstance(tool_arguments, dict):
        raise ValueError("Tool arguments must be a dictionary.")

    existing = _get_matching_pending_approval(
        db,
        task_id=task_id,
        tool_name=tool_name,
        tool_arguments=tool_arguments,
    )

    if existing is not None:
        return existing

    approval = ApprovalRequest(
        task_id=task_id,
        tool_name=tool_name,
        tool_arguments=tool_arguments,
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
        db.rollback()

        # A concurrent request may have created the pending approval.
        # Reuse it only if its saved arguments match exactly.
        existing = _get_matching_pending_approval(
            db,
            task_id=task_id,
            tool_name=tool_name,
            tool_arguments=tool_arguments,
        )

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


def _decide_request(
    db: Session,
    *,
    approval_id: int,
    decided_by: str,
    new_status: ApprovalStatus,
    event_type: str,
) -> ApprovalRequest:
    """
    Atomically transition a pending approval to its final decision.

    The status update and audit event are committed together. If audit
    recording fails, the transaction is rolled back.
    """
    decided_by = decided_by.strip()

    if not decided_by:
        raise ValueError("Decision-maker identity cannot be empty.")

    now = datetime.now(timezone.utc)

    try:
        result = db.execute(
            update(ApprovalRequest)
            .where(
                ApprovalRequest.id == approval_id,
                ApprovalRequest.status == ApprovalStatus.PENDING.value,
            )
            .values(
                status=new_status.value,
                decided_by=decided_by,
                decided_at=now,
            )
        )

        if result.rowcount != 1:
            db.rollback()

            approval = db.get(ApprovalRequest, approval_id)

            if approval is None:
                raise ApprovalNotFoundError(
                    f"Approval request not found: {approval_id}"
                )

            raise InvalidApprovalStateError(
                f"Approval request {approval_id} is already "
                f"{approval.status} and cannot be changed."
            )

        record_audit_event(
            db=db,
            task_id=db.execute(
                select(ApprovalRequest.task_id).where(
                    ApprovalRequest.id == approval_id
                )
            ).scalar_one(),
            event_type=event_type,
            actor=decided_by,
            details={
                "approval_id": approval_id,
                "status": new_status.value,
            },
            commit=False,
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    return get_approval(db=db, approval_id=approval_id)


def approve_request(
    db: Session,
    approval_id: int,
    decided_by: str,
) -> ApprovalRequest:
    return _decide_request(
        db,
        approval_id=approval_id,
        decided_by=decided_by,
        new_status=ApprovalStatus.APPROVED,
        event_type="approval.granted",
    )


def reject_request(
    db: Session,
    approval_id: int,
    decided_by: str,
) -> ApprovalRequest:
    return _decide_request(
        db,
        approval_id=approval_id,
        decided_by=decided_by,
        new_status=ApprovalStatus.REJECTED,
        event_type="approval.rejected",
    )