from app.agents.schemas import AgentPlan
from app.agents.state import AgentStatus
from app.approval_service import approve_request
from app.llm.fake import FakeLLMProvider
from app.models import Task
from app.workflow_runner import WorkflowRunner


def test_workflow_runner_starts_workflow():
    plan = AgentPlan(
        reasoning_summary="Investigate payment failures.",
        tool_call={
            "tool": "sql.read",
            "arguments": {
                "query": "SELECT COUNT(*) FROM payment_failures",
            },
        },
    )

    runner = WorkflowRunner(
        FakeLLMProvider(plan)
    )

    state = {
        "task_id": 100,
        "user_id": "user-123",
        "request": "Investigate payment failures",
        "status": AgentStatus.IDLE,
    }

    result = runner.start(
        state,
        thread_id="task-100",
    )

    assert result["status"] == AgentStatus.COMPLETED
    assert result["tool_result"]["tool"] == "sql.read"


def test_workflow_runner_resumes_approval(db_session):
    plan = AgentPlan(
        reasoning_summary="Restart the payment worker.",
        tool_call={
            "tool": "service.restart",
            "arguments": {
                "service": "payment-worker",
            },
        },
    )

    # Create the real parent task because ApprovalRequest.task_id
    # has a foreign-key relationship to tasks.id.
    task = Task(
        user_id="manager-123",
        request="Restart the payment worker",
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    runner = WorkflowRunner(
        FakeLLMProvider(plan),
        db=db_session,
    )

    state = {
    "task_id": task.id,
    "user_id": "manager-123",
    "request": "Restart the payment worker",
    "status": AgentStatus.IDLE,
    }

    thread_id = f"task-{task.id}"

    # ---------------------------------------------------------
    # 1. Start workflow
    # ---------------------------------------------------------

    first_result = runner.start(
        state,
        thread_id=thread_id,
    )

    # The high-risk operation must pause for human approval.
    assert "__interrupt__" in first_result

    # The tool execution node should have created an approval.
    approval_id = first_result["approval_id"]

    assert approval_id is not None
    assert first_result["status"] == AgentStatus.AWAITING_APPROVAL

    # ---------------------------------------------------------
    # 2. Simulate human approval
    # ---------------------------------------------------------

    approval = approve_request(
        db=db_session,
        approval_id=approval_id,
        decided_by="test-manager",
    )

    assert approval.status == "approved"
    assert approval.decided_by == "test-manager"

    # ---------------------------------------------------------
    # 3. Resume paused LangGraph workflow
    # ---------------------------------------------------------

    second_result = runner.resume(
        thread_id=thread_id,
        approved=True,
    )

    # The approved action executes, is verified, and the workflow
    # continues through the completion node.
    assert second_result["status"] == AgentStatus.COMPLETED

    # The workflow must record that approval was granted.
    assert second_result["approval_granted"] is True

    # Verify that the approved high-risk tool actually executed.
    assert second_result["tool_result"]["tool"] == "service.restart"
    assert second_result["tool_result"]["status"] == "simulated"
    assert second_result["tool_result"]["service"] == "payment-worker"