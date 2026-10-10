import json

from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from app.agents.nodes.approved_execution import (
    approved_execution_node,
)
from app.agents.state import AgentStatus
from app.approval_service import (
    approve_request,
    create_approval,
)
from app.models import AuditEvent, Task

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

def test_approved_execution_runs_tool(db_session):
    task = create_task(db_session)
    approval = create_pending_approval(
        db_session,
        task,
    )

    approve_request(
        db=db_session,
        approval_id=approval.id,
        decided_by="manager",
    )

    state = {
        "task_id": task.id,
        "selected_tool": "service.restart",
        "tool_arguments": {
            "service": "payment-worker",
        },
        "approval_id": approval.id,
        "user_id": "requester",
    }

    result = approved_execution_node(
        state,
        db=db_session,
    )
    assert result["status"] == AgentStatus.EXECUTING_ACTION
    assert result["approval_granted"] is True
    assert result["approval_decided_by"] == "manager"
    assert result["tool_result"]["tool"] == "service.restart"
    assert result["tool_result"]["status"] == "simulated"
    assert result["tool_result"]["service"] == "payment-worker"

    events = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.task_id == task.id)
        .order_by(AuditEvent.id)
        .all()
    )

    tool_events = [
        event
        for event in events
        if event.event_type in {
            "tool.invoked",
            "tool.completed",
        }
    ]

    assert [event.event_type for event in tool_events] == [
        "tool.invoked",
        "tool.completed",
    ]

    assert tool_events[0].actor == "manager"
    assert json.loads(tool_events[0].details) == {
        "tool_name": "service.restart",
        "risk_level": "high",
        "approval_id": approval.id,
        "approved_by": "manager",
    }

    assert tool_events[1].actor == "manager"
    assert json.loads(tool_events[1].details) == {
        "tool_name": "service.restart",
        "risk_level": "high",
        "approval_id": approval.id,
        "approved_by": "manager",
        "status": "success",
    }

def test_pending_approval_cannot_execute(db_session):
    task = create_task(db_session)
    approval = create_pending_approval(
        db_session,
        task,
    )

    state = {
        "task_id": task.id,
        "selected_tool": "service.restart",
        "tool_arguments": {
            "service": "payment-worker",
        },
        "approval_id": approval.id,
        "user_id": "requester",
    }

    result = approved_execution_node(
        state,
        db=db_session,
    )

    assert result["status"] == AgentStatus.FAILED
    assert "approved approval request" in result["error"]


def test_pending_approval_never_invokes_tool_registry(
    db_session,
    monkeypatch,
):
    task = create_task(db_session)
    approval = create_pending_approval(
        db_session,
        task,
    )

    executed = False

    class FakeRegistry:
        def execute(self, tool_name, arguments):
            nonlocal executed
            executed = True
            return {
                "tool": tool_name,
                "status": "should-not-execute",
            }

    monkeypatch.setattr(
        "app.agents.nodes.approved_execution.create_tool_registry",
        lambda: FakeRegistry(),
    )

    state = {
        "task_id": task.id,
        "selected_tool": "service.restart",
        "tool_arguments": {
            "service": "payment-worker",
        },
        "approval_id": approval.id,
        "user_id": "requester",
    }

    result = approved_execution_node(
        state,
        db=db_session,
    )

    assert result["status"] == AgentStatus.FAILED
    assert "approved approval request" in result["error"]
    assert executed is False

def test_wrong_tool_cannot_execute(db_session):
    task = create_task(db_session)
    approval = create_pending_approval(
        db_session,
        task,
    )

    approve_request(
        db=db_session,
        approval_id=approval.id,
        decided_by="manager",
    )

    state = {
        "task_id": task.id,
        "selected_tool": "sql.read",
        "tool_arguments": {
            "query": "SELECT 1",
        },
        "approval_id": approval.id,
        "user_id": "requester",
    }

    result = approved_execution_node(
        state,
        db=db_session,
    )

    assert result["status"] == AgentStatus.FAILED
    assert "does not authorize this tool" in result["error"]

def test_wrong_tool_never_invokes_tool_registry(
    db_session,
    monkeypatch,
):
    task = create_task(db_session)
    approval = create_pending_approval(
        db_session,
        task,
    )

    approve_request(
        db=db_session,
        approval_id=approval.id,
        decided_by="manager",
    )

    executed = False

    class FakeRegistry:
        def execute(self, tool_name, arguments):
            nonlocal executed
            executed = True
            return {
                "tool": tool_name,
                "status": "should-not-execute",
            }

    monkeypatch.setattr(
        "app.agents.nodes.approved_execution.create_tool_registry",
        lambda: FakeRegistry(),
    )

    state = {
        "task_id": task.id,
        "selected_tool": "sql.read",
        "tool_arguments": {
            "query": "SELECT 1",
        },
        "approval_id": approval.id,
        "user_id": "requester",
    }

    result = approved_execution_node(
        state,
        db=db_session,
    )

    assert result["status"] == AgentStatus.FAILED
    assert "does not authorize this tool" in result["error"]
    assert executed is False

def test_wrong_task_cannot_execute(db_session):
    task = create_task(db_session)

    other_task = Task(
        user_id="other-user",
        request="Another operation",
    )
    db_session.add(other_task)
    db_session.commit()
    db_session.refresh(other_task)

    approval = create_pending_approval(
        db_session,
        task,
    )

    approve_request(
        db=db_session,
        approval_id=approval.id,
        decided_by="manager",
    )

    state = {
        "task_id": other_task.id,
        "selected_tool": "service.restart",
        "tool_arguments": {
            "service": "payment-worker",
        },
        "approval_id": approval.id,
        "user_id": "requester",
    }

    result = approved_execution_node(
        state,
        db=db_session,
    )

    assert result["status"] == AgentStatus.FAILED
    assert "does not belong to this task" in result["error"]

def test_wrong_task_never_invokes_tool_registry(
    db_session,
    monkeypatch,
):
    task = create_task(db_session)

    other_task = Task(
        user_id="other-user",
        request="Another operation",
    )
    db_session.add(other_task)
    db_session.commit()
    db_session.refresh(other_task)

    approval = create_pending_approval(
        db_session,
        task,
    )

    approve_request(
        db=db_session,
        approval_id=approval.id,
        decided_by="manager",
    )

    executed = False

    class FakeRegistry:
        def execute(self, tool_name, arguments):
            nonlocal executed
            executed = True
            return {
                "tool": tool_name,
                "status": "should-not-execute",
            }

    monkeypatch.setattr(
        "app.agents.nodes.approved_execution.create_tool_registry",
        lambda: FakeRegistry(),
    )

    state = {
        "task_id": other_task.id,
        "selected_tool": "service.restart",
        "tool_arguments": {
            "service": "payment-worker",
        },
        "approval_id": approval.id,
        "user_id": "requester",
    }

    result = approved_execution_node(
        state,
        db=db_session,
    )

    assert result["status"] == AgentStatus.FAILED
    assert "does not belong to this task" in result["error"]
    assert executed is False

def test_missing_approval_id_cannot_execute(db_session):
    task = create_task(db_session)

    state = {
        "task_id": task.id,
        "selected_tool": "service.restart",
        "tool_arguments": {
            "service": "payment-worker",
        },
        "user_id": "requester",
    }

    result = approved_execution_node(
        state,
        db=db_session,
    )

    assert result["status"] == AgentStatus.FAILED
    assert "approval_id" in result["error"]

def test_approved_execution_records_actual_approver(
    db_session,
):
    task = create_task(db_session)

    approval = create_pending_approval(
        db_session,
        task,
    )

    approve_request(
        db=db_session,
        approval_id=approval.id,
        decided_by="admin-123",
    )

    state = {
        "task_id": task.id,
        "selected_tool": "service.restart",
        "tool_arguments": {
            "service": "payment-worker",
        },
        "approval_id": approval.id,
        "user_id": "requester",
    }

    result = approved_execution_node(
        state,
        db=db_session,
    )

    assert result["status"] == AgentStatus.EXECUTING_ACTION
    assert result["approval_decided_by"] == "admin-123"

    events = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.task_id == task.id)
        .order_by(AuditEvent.id)
        .all()
    )

    tool_events = [
        event
        for event in events
        if event.event_type in {
            "tool.invoked",
            "tool.completed",
        }
    ]

    assert tool_events[0].actor == "admin-123"
    assert tool_events[1].actor == "admin-123"

    assert (
        json.loads(tool_events[0].details)["approved_by"]
        == "admin-123"
    )

    assert (
        json.loads(tool_events[1].details)["approved_by"]
        == "admin-123"
    )

def test_approved_execution_rejects_approval_without_approver_identity(
    db_session,
):
    task = create_task(db_session)

    approval = create_pending_approval(
        db_session,
        task,
    )

    approve_request(
        db=db_session,
        approval_id=approval.id,
        decided_by="manager",
    )

    approval.decided_by = None
    db_session.commit()

    state = {
        "task_id": task.id,
        "selected_tool": "service.restart",
        "tool_arguments": {
            "service": "payment-worker",
        },
        "approval_id": approval.id,
        "user_id": "requester",
    }

    result = approved_execution_node(
        state,
        db=db_session,
    )

    assert result["status"] == AgentStatus.FAILED
    assert (
        result["error"]
        == "Approved action is missing the identity of the approver."
    )

def test_concurrent_approved_execution_runs_tool_only_once(
    db_session,
    monkeypatch,
):
    task = create_task(db_session)

    approval = create_pending_approval(
        db_session,
        task,
    )

    approve_request(
        db=db_session,
        approval_id=approval.id,
        decided_by="manager",
    )

    execution_count = 0
    execution_lock = Lock()

    class CountingRegistry:
        def execute(self, tool_name, arguments):
            nonlocal execution_count

            with execution_lock:
                execution_count += 1

            return {
                "tool": tool_name,
                "status": "simulated",
                "service": arguments["service"],
            }

    monkeypatch.setattr(
        "app.agents.nodes.approved_execution.create_tool_registry",
        lambda: CountingRegistry(),
    )

    state = {
        "task_id": task.id,
        "selected_tool": "service.restart",
        "tool_arguments": {
            "service": "payment-worker",
        },
        "approval_id": approval.id,
        "user_id": "requester",
    }

    def execute():
        from app.db import SessionLocal

        session = SessionLocal()

        try:
            return approved_execution_node(
                state,
                db=session,
            )
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_one = executor.submit(execute)
        future_two = executor.submit(execute)

        result_one = future_one.result()
        result_two = future_two.result()

    results = [
        result_one,
        result_two,
    ]

    assert execution_count == 1

    successful = [
        result
        for result in results
        if result["status"] == AgentStatus.EXECUTING_ACTION
    ]

    failed = [
        result
        for result in results
        if result["status"] == AgentStatus.FAILED
    ]

    assert len(successful) == 1
    assert len(failed) == 1

def test_failed_claimed_execution_cannot_be_retried(
    db_session,
    monkeypatch,
):
    task = create_task(db_session)

    approval = create_pending_approval(
        db_session,
        task,
    )

    approve_request(
        db=db_session,
        approval_id=approval.id,
        decided_by="manager",
    )

    execution_count = 0

    class FailingRegistry:
        def execute(self, tool_name, arguments):
            nonlocal execution_count
            execution_count += 1

            raise ValueError(
                "Payment worker restart failed."
            )

    monkeypatch.setattr(
        "app.agents.nodes.approved_execution.create_tool_registry",
        lambda: FailingRegistry(),
    )

    state = {
        "task_id": task.id,
        "selected_tool": "service.restart",
        "tool_arguments": {
            "service": "payment-worker",
        },
        "approval_id": approval.id,
        "user_id": "requester",
    }

    first_result = approved_execution_node(
        state,
        db=db_session,
    )

    assert first_result["status"] == AgentStatus.FAILED
    assert (
        first_result["error"]
        == "Payment worker restart failed."
    )

    assert execution_count == 1

    db_session.expire_all()

    persisted_approval = db_session.get(
        type(approval),
        approval.id,
    )

    assert persisted_approval is not None
    assert persisted_approval.execution_claimed_at is not None
    assert (
        persisted_approval.execution_claimed_by
        == "manager"
    )

    second_result = approved_execution_node(
        state,
        db=db_session,
    )

    assert second_result["status"] == AgentStatus.FAILED
    assert (
        second_result["error"]
        == "Approved action has already been claimed for execution."
    )

    assert execution_count == 1

    events = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.task_id == task.id)
        .order_by(AuditEvent.id)
        .all()
    )

    tool_events = [
        event
        for event in events
        if event.event_type in {
            "tool.invoked",
            "tool.completed",
        }
    ]

    assert [event.event_type for event in tool_events] == [
        "tool.invoked",
        "tool.completed",
    ]

    assert tool_events[0].actor == "manager"
    assert json.loads(tool_events[0].details)["approved_by"] == "manager"

    assert tool_events[1].actor == "manager"

    completed_details = json.loads(
        tool_events[1].details
    )

    assert completed_details["status"] == "failed"
    assert (
        completed_details["error"]
        == "Payment worker restart failed."
    )

def test_audit_failure_after_claim_does_not_repeat_execution(
    db_session,
    monkeypatch,
):
    task = create_task(db_session)

    approval = create_pending_approval(
        db_session,
        task,
    )

    approve_request(
        db=db_session,
        approval_id=approval.id,
        decided_by="manager",
    )

    execution_count = 0

    class CountingRegistry:
        def execute(self, tool_name, arguments):
            nonlocal execution_count
            execution_count += 1

            return {
                "tool": tool_name,
                "status": "simulated",
                "service": arguments["service"],
            }

    monkeypatch.setattr(
        "app.agents.nodes.approved_execution.create_tool_registry",
        lambda: CountingRegistry(),
    )

    original_record_audit_event = (
        "app.agents.nodes.approved_execution.record_audit_event"
    )

    audit_call_count = 0

    def failing_audit(*args, **kwargs):
        nonlocal audit_call_count
        audit_call_count += 1

        raise RuntimeError(
            "Audit service unavailable."
        )

    monkeypatch.setattr(
        original_record_audit_event,
        failing_audit,
    )

    state = {
        "task_id": task.id,
        "selected_tool": "service.restart",
        "tool_arguments": {
            "service": "payment-worker",
        },
        "approval_id": approval.id,
        "user_id": "requester",
    }

    first_result = approved_execution_node(
        state,
        db=db_session,
    )

    assert first_result["status"] == AgentStatus.FAILED
    assert (
        first_result["error"]
        == "Audit service unavailable."
    )

    assert execution_count == 0
    assert audit_call_count == 1

    db_session.expire_all()

    persisted_approval = db_session.get(
        type(approval),
        approval.id,
    )

    assert persisted_approval is not None
    assert persisted_approval.execution_claimed_at is None
    assert persisted_approval.execution_claimed_by is None


def test_completion_audit_failure_does_not_repeat_execution(
    db_session,
    monkeypatch,
):
    task = create_task(db_session)

    approval = create_pending_approval(
        db_session,
        task,
    )

    approve_request(
        db=db_session,
        approval_id=approval.id,
        decided_by="manager",
    )

    execution_count = 0
    audit_call_count = 0

    class CountingRegistry:
        def execute(self, tool_name, arguments):
            nonlocal execution_count
            execution_count += 1
            return {
                "tool": tool_name,
                "status": "simulated",
                "service": arguments["service"],
            }

    monkeypatch.setattr(
        "app.agents.nodes.approved_execution.create_tool_registry",
        lambda: CountingRegistry(),
    )

    def failing_completion_audit(*args, **kwargs):
        nonlocal audit_call_count
        audit_call_count += 1

        if kwargs.get("event_type") == "tool.completed":
            raise RuntimeError("Completion audit unavailable.")

        return record_audit_event_original(*args, **kwargs)

    from app.audit.service import record_audit_event as record_audit_event_original

    monkeypatch.setattr(
        "app.agents.nodes.approved_execution.record_audit_event",
        failing_completion_audit,
    )

    state = {
        "task_id": task.id,
        "selected_tool": "service.restart",
        "tool_arguments": {"service": "payment-worker"},
        "approval_id": approval.id,
        "user_id": "requester",
    }

    first_result = approved_execution_node(state, db=db_session)

    assert first_result["status"] == AgentStatus.FAILED
    assert "completion audit failed" in first_result["error"].lower()
    assert execution_count == 1

    db_session.expire_all()
    persisted_approval = db_session.get(type(approval), approval.id)

    assert persisted_approval is not None
    assert persisted_approval.execution_claimed_at is not None

    second_result = approved_execution_node(state, db=db_session)

    assert second_result["status"] == AgentStatus.FAILED
    assert "already been claimed" in second_result["error"].lower()
    assert execution_count == 1


def test_unexpected_tool_exception_is_handled_and_cannot_be_retried(
    db_session,
    monkeypatch,
):
    task = create_task(db_session)
    approval = create_pending_approval(db_session, task)

    approve_request(
        db=db_session,
        approval_id=approval.id,
        decided_by="manager",
    )

    execution_count = 0

    class UnexpectedFailureRegistry:
        def execute(self, tool_name, arguments):
            nonlocal execution_count
            execution_count += 1
            raise RuntimeError("Unexpected executor failure.")

    monkeypatch.setattr(
        "app.agents.nodes.approved_execution.create_tool_registry",
        lambda: UnexpectedFailureRegistry(),
    )

    state = {
        "task_id": task.id,
        "selected_tool": "service.restart",
        "tool_arguments": {"service": "payment-worker"},
        "approval_id": approval.id,
        "user_id": "requester",
    }

    first_result = approved_execution_node(state, db=db_session)

    assert first_result["status"] == AgentStatus.FAILED
    assert first_result["error"] == "Unexpected executor failure."
    assert execution_count == 1

    db_session.expire_all()
    persisted_approval = db_session.get(type(approval), approval.id)

    assert persisted_approval is not None
    assert persisted_approval.execution_claimed_at is not None

    second_result = approved_execution_node(state, db=db_session)

    assert second_result["status"] == AgentStatus.FAILED
    assert "already been claimed" in second_result["error"].lower()
    assert execution_count == 1
