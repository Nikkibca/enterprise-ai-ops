from app.agents.nodes.tool_execution import tool_execution_node
from app.agents.state import AgentStatus
from app.models import ApprovalRequest, ApprovalStatus


def test_high_risk_tool_creates_persistent_approval(db_session):
    from app.models import Task

    task = Task(
        user_id="manager-123",
        request="Restart payment worker",
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

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