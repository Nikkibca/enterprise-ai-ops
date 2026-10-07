import json

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

    assert tool_events[0].actor == "requester"
    assert json.loads(tool_events[0].details) == {
        "tool_name": "service.restart",
        "risk_level": "high",
        "approval_id": approval.id,
    }

    assert tool_events[1].actor == "requester"
    assert json.loads(tool_events[1].details) == {
        "tool_name": "service.restart",
        "risk_level": "high",
        "approval_id": approval.id,
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

