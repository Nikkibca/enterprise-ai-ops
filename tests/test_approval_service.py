
import pytest

from app.approval_service import (
    ApprovalNotFoundError,
    InvalidApprovalStateError,
    approve_request,
    create_approval,
    get_approval,
    reject_request,
)
from app.models import ApprovalRequest, ApprovalStatus, AuditEvent, Task

from concurrent.futures import ThreadPoolExecutor

from app.approval_service import approve_request
from app.db import SessionLocal
from app.models import (
    ApprovalRequest,
    ApprovalStatus,
    Task,
    TaskStatus,
)

def test_concurrent_approval_and_rejection_only_allow_one_decision(
    db_session,
):
    task = Task(
        user_id="requester-123",
        request="Restart payment worker",
        status=TaskStatus.CREATED.value,
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    approval = ApprovalRequest(
        task_id=task.id,
        tool_name="service.restart",
        risk_level="high",
        requested_by="requester-123",
        reason="High-risk operation requires human approval.",
        status=ApprovalStatus.PENDING.value,
    )

    db_session.add(approval)
    db_session.commit()
    db_session.refresh(approval)

    approval_id = approval.id

    def decide(decision: str, user_id: str):
        session = SessionLocal()

        try:
            if decision == "approve":
                result = approve_request(
                    db=session,
                    approval_id=approval_id,
                    decided_by=user_id,
                )
            else:
                result = reject_request(
                    db=session,
                    approval_id=approval_id,
                    decided_by=user_id,
                )

            return {
                "success": True,
                "decision": decision,
                "user_id": user_id,
                "result": result,
            }

        except InvalidApprovalStateError as exc:
            session.rollback()

            return {
                "success": False,
                "decision": decision,
                "user_id": user_id,
                "error": exc,
            }

        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        approve_future = executor.submit(
            decide,
            "approve",
            "manager-001",
        )

        reject_future = executor.submit(
            decide,
            "reject",
            "manager-002",
        )

        approve_result = approve_future.result()
        reject_result = reject_future.result()

    results = [
        approve_result,
        reject_result,
    ]

    successful = [
        result
        for result in results
        if result["success"]
    ]

    failed = [
        result
        for result in results
        if not result["success"]
    ]

    assert len(successful) == 1
    assert len(failed) == 1

    assert isinstance(
        failed[0]["error"],
        InvalidApprovalStateError,
    )

    db_session.expire_all()

    final_approval = db_session.get(
        ApprovalRequest,
        approval_id,
    )

    assert final_approval is not None

    assert final_approval.status in {
        ApprovalStatus.APPROVED.value,
        ApprovalStatus.REJECTED.value,
    }

    assert final_approval.decided_by in {
        "manager-001",
        "manager-002",
    }

    assert final_approval.decided_at is not None

def test_concurrent_approval_requests_only_allow_one_decision(
    db_session,
):
    task = Task(
        user_id="requester-123",
        request="Restart payment worker",
        status=TaskStatus.CREATED.value,
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    approval = ApprovalRequest(
        task_id=task.id,
        tool_name="service.restart",
        risk_level="high",
        requested_by="requester-123",
        reason="High-risk operation requires human approval.",
        status=ApprovalStatus.PENDING.value,
    )

    db_session.add(approval)
    db_session.commit()
    db_session.refresh(approval)

    approval_id = approval.id

    def approve_as(user_id: str):
        session = SessionLocal()

        try:
            result = approve_request(
                db=session,
                approval_id=approval_id,
                decided_by=user_id,
            )

            return {
                "user_id": user_id,
                "success": True,
                "result": result,
            }

        except Exception as exc:
            session.rollback()

            return {
                "user_id": user_id,
                "success": False,
                "error": exc,
            }

        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_one = executor.submit(
            approve_as,
            "manager-001",
        )

        future_two = executor.submit(
            approve_as,
            "manager-002",
        )

        result_one = future_one.result()
        result_two = future_two.result()

    results = [
        result_one,
        result_two,
    ]

    successful = [
        result
        for result in results
        if result["success"]
    ]

    failed = [
        result
        for result in results
        if not result["success"]
    ]

    assert len(successful) == 1
    assert len(failed) == 1

    db_session.expire_all()

    final_approval = db_session.get(
        ApprovalRequest,
        approval_id,
    )

    assert final_approval is not None

    assert (
        final_approval.status
        == ApprovalStatus.APPROVED.value
    )

    assert final_approval.decided_by in {
        "manager-001",
        "manager-002",
    }

    assert final_approval.decided_at is not None

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

    persisted = get_approval(
        db=db_session,
        approval_id=approval.id,
    )

    assert persisted.status == ApprovalStatus.APPROVED.value
    assert persisted.decided_by == "manager-456"


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

    persisted = get_approval(
        db=db_session,
        approval_id=approval.id,
    )

    assert persisted.status == ApprovalStatus.REJECTED.value
    assert persisted.decided_by == "manager-456"


def test_approved_request_cannot_be_rejected(db_session):
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
        reject_request(
            db=db_session,
            approval_id=approval.id,
            decided_by="manager-789",
        )

    persisted = get_approval(
        db=db_session,
        approval_id=approval.id,
    )

    assert persisted.status == ApprovalStatus.APPROVED.value
    assert persisted.decided_by == "manager-456"


def test_rejected_request_cannot_be_approved(db_session):
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
        approve_request(
            db=db_session,
            approval_id=approval.id,
            decided_by="manager-789",
        )

    persisted = get_approval(
        db=db_session,
        approval_id=approval.id,
    )

    assert persisted.status == ApprovalStatus.REJECTED.value
    assert persisted.decided_by == "manager-456"


def test_create_approval_reuses_existing_pending_approval(db_session):
    task = create_test_task(db_session)

    first = create_approval(
        db=db_session,
        task_id=task.id,
        tool_name="service.restart",
        risk_level="high",
        requested_by="user-123",
        reason="Requires approval.",
    )

    second = create_approval(
        db=db_session,
        task_id=task.id,
        tool_name="service.restart",
        risk_level="high",
        requested_by="user-123",
        reason="Requires approval.",
    )

    assert second.id == first.id

    approvals = (
        db_session.query(ApprovalRequest)
        .filter(
            ApprovalRequest.task_id == task.id,
            ApprovalRequest.tool_name == "service.restart",
        )
        .all()
    )

    assert len(approvals) == 1
    assert approvals[0].status == ApprovalStatus.PENDING.value

    events = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.task_id == task.id)
        .all()
    )

    assert len(events) == 1
    assert events[0].event_type == "approval.requested"


def test_approve_request_rolls_back_when_audit_fails(
    db_session,
    monkeypatch,
):
    task = create_test_task(db_session)

    approval = create_approval(
        db=db_session,
        task_id=task.id,
        tool_name="service.restart",
        risk_level="high",
        requested_by="user-123",
        reason="Requires approval.",
    )

    def failing_audit(*args, **kwargs):
        raise RuntimeError("Simulated audit failure")

    import app.approval_service as approval_service

    monkeypatch.setattr(
        approval_service,
        "record_audit_event",
        failing_audit,
    )

    with pytest.raises(
        RuntimeError,
        match="Simulated audit failure",
    ):
        approve_request(
            db=db_session,
            approval_id=approval.id,
            decided_by="manager-456",
        )

    db_session.rollback()

    persisted = get_approval(
        db=db_session,
        approval_id=approval.id,
    )

    assert persisted.status == ApprovalStatus.PENDING.value
    assert persisted.decided_by is None
    assert persisted.decided_at is None

    events = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.task_id == task.id)
        .all()
    )

    assert len(events) == 1
    assert events[0].event_type == "approval.requested"


def test_reject_request_rolls_back_when_audit_fails(
    db_session,
    monkeypatch,
):
    task = create_test_task(db_session)

    approval = create_approval(
        db=db_session,
        task_id=task.id,
        tool_name="service.restart",
        risk_level="high",
        requested_by="user-123",
        reason="Requires approval.",
    )

    def failing_audit(*args, **kwargs):
        raise RuntimeError("Simulated audit failure")

    import app.approval_service as approval_service

    monkeypatch.setattr(
        approval_service,
        "record_audit_event",
        failing_audit,
    )

    with pytest.raises(
        RuntimeError,
        match="Simulated audit failure",
    ):
        reject_request(
            db=db_session,
            approval_id=approval.id,
            decided_by="manager-456",
        )

    db_session.rollback()

    persisted = get_approval(
        db=db_session,
        approval_id=approval.id,
    )

    assert persisted.status == ApprovalStatus.PENDING.value
    assert persisted.decided_by is None
    assert persisted.decided_at is None

    events = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.task_id == task.id)
        .all()
    )

    assert len(events) == 1
    assert events[0].event_type == "approval.requested"

