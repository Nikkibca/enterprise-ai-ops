import json

from app.agents.nodes.tool_execution import tool_execution_node
from app.agents.state import AgentStatus
from app.models import ApprovalRequest, ApprovalStatus, AuditEvent, Task


def create_task(db_session, user_id="user-123", request="Test task"):
    task = Task(
        user_id=user_id,
        request=request,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


def get_audit_events(db_session, task_id):
    return (
        db_session.query(AuditEvent)
        .filter(AuditEvent.task_id == task_id)
        .order_by(AuditEvent.id)
        .all()
    )


def test_low_risk_knowledge_tool_executes():
    state = {
        "selected_tool": "knowledge.search",
        "tool_arguments": {
            "query": "payment timeout",
        },
        "user_id": "user-123",
    }

    result = tool_execution_node(state)

    assert result["status"] == AgentStatus.EXECUTING_TOOL
    assert result["risk_level"] == "low"
    assert result["approval_required"] is False
    assert result["approval_granted"] is False
    assert result["tool_result"]["tool"] == "knowledge.search"


def test_low_risk_sql_tool_executes():
    state = {
        "selected_tool": "sql.read",
        "tool_arguments": {
            "query": "SELECT 1",
        },
        "user_id": "user-123",
    }

    result = tool_execution_node(state)

    assert result["status"] == AgentStatus.EXECUTING_TOOL
    assert result["risk_level"] == "low"
    assert result["approval_required"] is False
    assert result["tool_result"] is not None


def test_medium_risk_python_tool_executes():
    state = {
        "selected_tool": "python.analysis",
        "tool_arguments": {
            "operation": "summary",
            "values": [10, 20, 30],
        },
        "user_id": "user-123",
    }

    result = tool_execution_node(state)

    assert result["status"] == AgentStatus.EXECUTING_TOOL
    assert result["risk_level"] == "medium"
    assert result["approval_required"] is False
    assert result["tool_result"]["operation"] == "summary"


def test_unknown_tool_is_rejected():
    state = {
        "selected_tool": "shell.execute",
        "tool_arguments": {},
        "user_id": "user-123",
    }

    result = tool_execution_node(state)

    assert result["status"] == AgentStatus.FAILED
    assert "not allowed" in result["error"]


def test_missing_tool_is_rejected():
    state = {
        "selected_tool": "",
        "tool_arguments": {},
        "user_id": "user-123",
    }

    result = tool_execution_node(state)

    assert result["status"] == AgentStatus.FAILED
    assert result["error"]


def test_unknown_user_is_denied():
    state = {
        "selected_tool": "knowledge.search",
        "tool_arguments": {
            "query": "payment timeout",
        },
        "user_id": "unknown-user",
    }

    result = tool_execution_node(state)

    assert result["status"] == AgentStatus.FAILED
    assert "lacks required permission" in result["error"]


def test_operations_engineer_cannot_restart_service():
    state = {
        "selected_tool": "service.restart",
        "tool_arguments": {
            "service": "payment-worker",
        },
        "user_id": "user-123",
    }

    result = tool_execution_node(state)

    assert result["status"] == AgentStatus.FAILED
    assert result["approval_required"] is False
    assert "lacks required permission" in result["error"]


def test_high_risk_tool_requires_approval_without_database():
    state = {
        "selected_tool": "service.restart",
        "tool_arguments": {
            "service": "payment-worker",
        },
        "user_id": "manager-123",
    }

    result = tool_execution_node(state)

    assert result["status"] == AgentStatus.AWAITING_APPROVAL
    assert result["risk_level"] == "high"
    assert result["approval_required"] is True
    assert result["approval_granted"] is False


def test_high_risk_tool_requires_task_id_with_database(db_session):
    state = {
        "selected_tool": "service.restart",
        "tool_arguments": {
            "service": "payment-worker",
        },
        "user_id": "manager-123",
    }

    result = tool_execution_node(
        state,
        db=db_session,
    )

    assert result["status"] == AgentStatus.FAILED
    assert result["approval_required"] is True
    assert "task_id" in result["error"]


def test_high_risk_tool_creates_approval_request(db_session):
    task = create_task(
        db_session,
        user_id="manager-123",
        request="Restart payment worker",
    )

    state = {
        "task_id": task.id,
        "selected_tool": "service.restart",
        "tool_arguments": {
            "service": "payment-worker",
        },
        "user_id": "manager-123",
    }

    result = tool_execution_node(
        state,
        db=db_session,
    )

    assert result["status"] == AgentStatus.AWAITING_APPROVAL
    assert result["approval_required"] is True
    assert result["approval_granted"] is False
    assert result["approval_id"] is not None

    approval = db_session.get(
        ApprovalRequest,
        result["approval_id"],
    )

    assert approval is not None
    assert approval.task_id == task.id
    assert approval.tool_name == "service.restart"
    assert approval.risk_level == "high"
    assert approval.requested_by == "manager-123"
    assert approval.status == ApprovalStatus.PENDING.value


def test_low_risk_policy_decision_is_audited(db_session):
    task = create_task(db_session)

    state = {
        "task_id": task.id,
        "selected_tool": "knowledge.search",
        "tool_arguments": {
            "query": "payment timeout",
        },
        "user_id": "user-123",
    }

    result = tool_execution_node(
        state,
        db=db_session,
    )

    assert result["status"] == AgentStatus.EXECUTING_TOOL

    events = get_audit_events(
        db_session,
        task.id,
    )

    assert events[0].event_type == "policy.checked"

    details = json.loads(events[0].details)

    assert details["tool_name"] == "knowledge.search"
    assert details["decision"] == "allow"
    assert details["risk_level"] == "low"
    assert details["role"] == "operations_engineer"
    assert details["required_permission"] == "knowledge.read"


def test_denied_policy_decision_is_audited(db_session):
    task = create_task(
        db_session,
        user_id="user-123",
        request="Restart payment worker",
    )

    state = {
        "task_id": task.id,
        "selected_tool": "service.restart",
        "tool_arguments": {
            "service": "payment-worker",
        },
        "user_id": "user-123",
    }

    result = tool_execution_node(
        state,
        db=db_session,
    )

    assert result["status"] == AgentStatus.FAILED

    events = get_audit_events(
        db_session,
        task.id,
    )

    assert len(events) == 1
    assert events[0].event_type == "policy.checked"

    details = json.loads(events[0].details)

    assert details["tool_name"] == "service.restart"
    assert details["decision"] == "deny"
    assert details["risk_level"] == "high"
    assert details["role"] == "operations_engineer"
    assert details["required_permission"] == "operations.restart"


def test_allowed_tool_invocation_is_audited(db_session):
    task = create_task(db_session)

    state = {
        "task_id": task.id,
        "selected_tool": "knowledge.search",
        "tool_arguments": {
            "query": "payment timeout",
        },
        "user_id": "user-123",
    }

    result = tool_execution_node(
        state,
        db=db_session,
    )

    assert result["status"] == AgentStatus.EXECUTING_TOOL

    events = get_audit_events(
        db_session,
        task.id,
    )

    assert events[1].event_type == "tool.invoked"

    details = json.loads(events[1].details)

    assert details["tool_name"] == "knowledge.search"
    assert details["risk_level"] == "low"
    assert details["role"] == "operations_engineer"


def test_successful_tool_completion_is_audited(db_session):
    task = create_task(db_session)

    state = {
        "task_id": task.id,
        "selected_tool": "knowledge.search",
        "tool_arguments": {
            "query": "payment timeout",
        },
        "user_id": "user-123",
    }

    result = tool_execution_node(
        state,
        db=db_session,
    )

    assert result["status"] == AgentStatus.EXECUTING_TOOL

    events = get_audit_events(
        db_session,
        task.id,
    )

    assert events[2].event_type == "tool.completed"

    details = json.loads(events[2].details)

    assert details["tool_name"] == "knowledge.search"
    assert details["risk_level"] == "low"
    assert details["role"] == "operations_engineer"
    assert details["status"] == "success"


def test_high_risk_approval_does_not_execute_tool(db_session):
    task = create_task(
        db_session,
        user_id="manager-123",
        request="Restart payment worker",
    )

    state = {
        "task_id": task.id,
        "selected_tool": "service.restart",
        "tool_arguments": {
            "service": "payment-worker",
        },
        "user_id": "manager-123",
    }

    result = tool_execution_node(
        state,
        db=db_session,
    )

    assert result["status"] == AgentStatus.AWAITING_APPROVAL
    assert result["approval_required"] is True
    assert result["approval_granted"] is False
    assert "tool_result" not in result

    events = get_audit_events(
        db_session,
        task.id,
    )

    event_types = [event.event_type for event in events]

    assert "policy.checked" in event_types
    assert "approval.requested" in event_types
    assert "tool.invoked" not in event_types
    assert "tool.completed" not in event_types
