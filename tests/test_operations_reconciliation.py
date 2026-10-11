import json
from datetime import datetime, timezone

from app.audit.service import record_audit_event
from app.models import ApprovalRequest, AuditEvent, Task
from app.operations_reconciliation import (
    get_execution_reconciliation_report,
)


def create_claimed_approval(db, *, tool_name="service.restart"):
    task = Task(
        user_id="user-123",
        request="Restart the payment worker",
        status="executing",
    )
    db.add(task)
    db.flush()

    approval = ApprovalRequest(
        task_id=task.id,
        tool_name=tool_name,
        risk_level="high",
        requested_by="user-123",
        reason="Test approval",
        status="approved",
        decided_by="manager-123",
        decided_at=datetime.now(timezone.utc),
        execution_claimed_at=datetime.now(timezone.utc),
        execution_claimed_by="manager-123",
    )
    db.add(approval)
    db.flush()

    return task, approval


def test_report_includes_claim_without_completion(db_session):
    _, approval = create_claimed_approval(db_session)

    report = get_execution_reconciliation_report(db_session)

    assert report == [
        {
            "approval_id": approval.id,
            "task_id": approval.task_id,
            "tool_name": "service.restart",
            "claimed_at": approval.execution_claimed_at.isoformat(),
            "claimed_by": "manager-123",
            "outcome": "uncertain",
            "requires_manual_review": True,
        }
    ]


def test_report_excludes_claim_with_success_completion(db_session):
    task, approval = create_claimed_approval(db_session)
    record_audit_event(
        db_session,
        task_id=task.id,
        event_type="tool.completed",
        actor="manager-123",
        details={
            "approval_id": approval.id,
            "tool_name": approval.tool_name,
            "status": "success",
        },
    )

    assert get_execution_reconciliation_report(db_session) == []


def test_report_excludes_claim_with_failed_completion(db_session):
    task, approval = create_claimed_approval(db_session)
    record_audit_event(
        db_session,
        task_id=task.id,
        event_type="tool.completed",
        actor="manager-123",
        details={
            "approval_id": approval.id,
            "tool_name": approval.tool_name,
            "status": "failed",
        },
    )

    assert get_execution_reconciliation_report(db_session) == []


def test_report_matches_exact_approval_id(db_session):
    task, approval = create_claimed_approval(db_session)

    # A completion for a different approval ID must not count.
    record_audit_event(
        db_session,
        task_id=task.id,
        event_type="tool.completed",
        actor="manager-123",
        details={
            "approval_id": approval.id + 1000,
            "tool_name": approval.tool_name,
            "status": "success",
        },
    )

    report = get_execution_reconciliation_report(db_session)

    assert [item["approval_id"] for item in report] == [approval.id]


def test_report_ignores_malformed_completion_details(db_session):
    task, approval = create_claimed_approval(db_session)
    db_session.add(
        AuditEvent(
            task_id=task.id,
            event_type="tool.completed",
            actor="manager-123",
            details="{invalid-json",
        )
    )
    db_session.flush()

    report = get_execution_reconciliation_report(db_session)

    assert [item["approval_id"] for item in report] == [approval.id]


def test_report_does_not_modify_database_records(db_session):
    _, approval = create_claimed_approval(db_session)
    original_claimed_at = approval.execution_claimed_at
    original_claimed_by = approval.execution_claimed_by
    original_status = approval.status
    audit_count_before = db_session.query(AuditEvent).count()

    get_execution_reconciliation_report(db_session)

    db_session.refresh(approval)

    assert approval.execution_claimed_at == original_claimed_at
    assert approval.execution_claimed_by == original_claimed_by
    assert approval.status == original_status
    assert db_session.query(AuditEvent).count() == audit_count_before
