import pytest

from app.approval_service import (
    ApprovalNotFoundError,
    InvalidApprovalStateError,
    approve_request,
    create_approval,
    get_approval,
    reject_request,
)
from app.models import ApprovalStatus, AuditEvent, Task


def create_test_task(db):
    task = Task(
        user_id="user-123",
        request="Restart payment worker",
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return task


def test_create_approval(db_session):
    task = create_test_task(db_session)

    approval = create_approval(
        db=db_session,
        task_id=task.id,
        tool_name="service.restart",
        risk_level="high",
        requested_by="user-123",
        reason="High-risk operation requires human approval.",
    )

    assert approval.id is not None
    assert approval.task_id == task.id
    assert approval.tool_name == "service.restart"
    assert approval.risk_level == "high"
    assert approval.requested_by == "user-123"
    assert approval.status == ApprovalStatus.PENDING.value
    assert approval.requested_at is not None

    events = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.task_id == task.id)
        .all()
    )

    assert len(events) == 1
    assert events[0].event_type == "approval.requested"


def test_get_approval(db_session):
    task = create_test_task(db_session)

    created = create_approval(
        db=db_session,
        task_id=task.id,
        tool_name="service.restart",
        risk_level="high",
        requested_by="user-123",
        reason="Requires approval.",
    )

    result = get_approval(
        db=db_session,
        approval_id=created.id,
    )

    assert result.id == created.id
    assert result.status == ApprovalStatus.PENDING.value


def test_get_missing_approval_raises(db_session):
    with pytest.raises(ApprovalNotFoundError):
        get_approval(
            db=db_session,
            approval_id=999999,
        )


def test_approve_request(db_session):
    task = create_test_task(db_session)

    approval = create_approval(
        db=db_session,
        task_id=task.id,
        tool_name="service.restart",
        risk_level="high",
        requested_by="user-123",
        reason="Requires approval.",
    )

    result = approve_request(
        db=db_session,
        approval_id=approval.id,
        decided_by="manager-456",
    )

    assert result.status == ApprovalStatus.APPROVED.value
    assert result.decided_by == "manager-456"
    assert result.decided_at is not None

    events = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.task_id == task.id)
        .order_by(AuditEvent.id)
        .all()
    )

    assert len(events) == 2
    assert events[1].event_type == "approval.granted"


def test_reject_request(db_session):
    task = create_test_task(db_session)

    approval = create_approval(
        db=db_session,
        task_id=task.id,
        tool_name="service.restart",
        risk_level="high",
        requested_by="user-123",
        reason="Requires approval.",
    )

    result = reject_request(
        db=db_session,
        approval_id=approval.id,
        decided_by="manager-456",
    )

    assert result.status == ApprovalStatus.REJECTED.value
    assert result.decided_by == "manager-456"
    assert result.decided_at is not None

    events = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.task_id == task.id)
        .order_by(AuditEvent.id)
        .all()
    )

    assert len(events) == 2
    assert events[1].event_type == "approval.rejected"


def test_cannot_approve_already_approved_request(db_session):
    task = create_test_task(db_session)

    approval = create_approval(
        db=db_session,
        task_id=task.id,
        tool_name="service.restart",
        risk_level="high",
        requested_by="user-123",
        reason="Requires approval.",
    )

    approve_request(
        db=db_session,
        approval_id=approval.id,
        decided_by="manager-456",
    )

    with pytest.raises(InvalidApprovalStateError):
        approve_request(
            db=db_session,
            approval_id=approval.id,
            decided_by="manager-789",
        )


def test_cannot_reject_already_rejected_request(db_session):
    task = create_test_task(db_session)

    approval = create_approval(
        db=db_session,
        task_id=task.id,
        tool_name="service.restart",
        risk_level="high",
        requested_by="user-123",
        reason="Requires approval.",
    )

    reject_request(
        db=db_session,
        approval_id=approval.id,
        decided_by="manager-456",
    )

    with pytest.raises(InvalidApprovalStateError):
        reject_request(
            db=db_session,
            approval_id=approval.id,
            decided_by="manager-789",
        )