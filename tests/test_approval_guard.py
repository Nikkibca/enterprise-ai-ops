import pytest

from app.approval_guard import (
    ApprovalGuardError,
    require_approved_action,
)
from app.approval_service import (
    approve_request,
    create_approval,
    reject_request,
)
from app.models import ApprovalStatus, Task


def create_task(db_session):
    task = Task(
        user_id="requester",
        request="Restart payment worker",
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


def create_pending_approval(db_session, task):
    return create_approval(
        db=db_session,
        task_id=task.id,
        tool_name="service.restart",
        risk_level="high",
        requested_by="requester",
        reason="High-risk operation requires human approval.",
    )


def test_pending_approval_cannot_execute(db_session):
    task = create_task(db_session)
    approval = create_pending_approval(db_session, task)

    with pytest.raises(
        ApprovalGuardError,
        match="requires an approved approval request",
    ):
        require_approved_action(
            db_session,
            approval_id=approval.id,
            task_id=task.id,
            tool_name="service.restart",
        )


def test_rejected_approval_cannot_execute(db_session):
    task = create_task(db_session)
    approval = create_pending_approval(db_session, task)

    reject_request(
        db=db_session,
        approval_id=approval.id,
        decided_by="manager",
    )

    with pytest.raises(
        ApprovalGuardError,
        match="requires an approved approval request",
    ):
        require_approved_action(
            db_session,
            approval_id=approval.id,
            task_id=task.id,
            tool_name="service.restart",
        )


def test_approved_action_can_execute(db_session):
    task = create_task(db_session)
    approval = create_pending_approval(db_session, task)

    approve_request(
        db=db_session,
        approval_id=approval.id,
        decided_by="manager",
    )

    result = require_approved_action(
        db_session,
        approval_id=approval.id,
        task_id=task.id,
        tool_name="service.restart",
    )

    assert result is None


def test_approval_for_different_task_is_rejected(db_session):
    task = create_task(db_session)
    other_task = Task(
        user_id="other-user",
        request="Another operation",
    )
    db_session.add(other_task)
    db_session.commit()
    db_session.refresh(other_task)

    approval = create_pending_approval(db_session, task)

    approve_request(
        db=db_session,
        approval_id=approval.id,
        decided_by="manager",
    )

    with pytest.raises(
        ApprovalGuardError,
        match="does not belong to this task",
    ):
        require_approved_action(
            db_session,
            approval_id=approval.id,
            task_id=other_task.id,
            tool_name="service.restart",
        )


def test_approval_for_different_tool_is_rejected(db_session):
    task = create_task(db_session)

    approval = create_approval(
        db=db_session,
        task_id=task.id,
        tool_name="service.restart",
        risk_level="high",
        requested_by="requester",
        reason="High-risk operation requires human approval.",
    )

    approve_request(
        db=db_session,
        approval_id=approval.id,
        decided_by="manager",
    )

    with pytest.raises(
        ApprovalGuardError,
        match="does not authorize this tool",
    ):
        require_approved_action(
            db_session,
            approval_id=approval.id,
            task_id=task.id,
            tool_name="sql.read",
        )


def test_missing_approval_is_rejected(db_session):
    task = create_task(db_session)

    with pytest.raises(
        ApprovalGuardError,
        match="Approval request not found",
    ):
        require_approved_action(
            db_session,
            approval_id=999999,
            task_id=task.id,
            tool_name="service.restart",
        )