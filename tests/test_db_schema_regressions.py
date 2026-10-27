import json
import pytest
from sqlalchemy import select, text

from app.audit.service import record_audit_event
from app.models import ApprovalRequest, ApprovalStatus, AuditEvent, Task
from scripts.migrate_audit_details_json import main as migrate_audit_details_json


def test_audit_events_details_supports_json_operators(db_session):
    """
    Regression test for historical database error:
    'operator does not exist: text ->> unknown'
    when querying audit_events.details->>'success'.
    """
    task = Task(
        user_id="test-regression-user",
        request="Regression test for JSON query operator",
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    record_audit_event(
        db=db_session,
        task_id=task.id,
        event_type="tool.completed",
        actor="operator",
        details={
            "tool_name": "service.restart",
            "success": "true",
            "status": "success",
            "approval_id": 99,
        },
    )

    # Raw SQL execution using the ->> JSON operator
    result = db_session.execute(
        text(
            """
            SELECT details->>'success' AS success_val,
                   details->>'tool_name' AS tool_name
            FROM audit_events
            WHERE task_id = :task_id
            """
        ),
        {"task_id": task.id},
    ).mappings().one()

    assert result["success_val"] == "true"
    assert result["tool_name"] == "service.restart"


def test_approval_requests_persists_tool_arguments_properly(db_session):
    """
    Regression test for historical database error:
    'column "tool_args" does not exist' in approval_requests.
    Ensures 'tool_arguments' is the authoritative column and stores structured JSON.
    """
    task = Task(
        user_id="test-approval-user",
        request="Regression test for approval tool arguments",
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    arguments = {"service": "worker-cache", "grace_period_seconds": 30}
    approval = ApprovalRequest(
        task_id=task.id,
        tool_name="service.restart",
        tool_arguments=arguments,
        risk_level="high",
        requested_by="operator",
        reason="Restart cache worker",
        status=ApprovalStatus.PENDING.value,
    )
    db_session.add(approval)
    db_session.commit()
    db_session.refresh(approval)

    # Verify column existence and typed JSON access via ORM
    saved = db_session.get(ApprovalRequest, approval.id)
    assert saved is not None
    assert saved.tool_arguments == arguments
    assert saved.tool_arguments["service"] == "worker-cache"

    # Verify column existence via SQL query
    raw_row = db_session.execute(
        text(
            """
            SELECT tool_arguments->>'service' AS service_name
            FROM approval_requests
            WHERE id = :approval_id
            """
        ),
        {"approval_id": approval.id},
    ).mappings().one()

    assert raw_row["service_name"] == "worker-cache"


def test_migrate_audit_details_json_is_idempotent():
    """
    Ensure the migration script can be run multiple times safely without error.
    """
    # Calling main() again should detect that details is already JSON and take no destructive action
    migrate_audit_details_json()
