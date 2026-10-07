from app.agents.schemas import AgentPlan
from app.agents.state import AgentStatus
from app.llm.fake import FakeLLMProvider
from app.models import Task
from app.workflow_runner import WorkflowRunner
from app.workflow_service import (
    assign_workflow_thread,
    build_workflow_thread_id,
    start_task_workflow,
)


def test_build_workflow_thread_id(db_session):
    task = Task(
        user_id="test-user",
        request="Investigate payment failures",
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    assert build_workflow_thread_id(task) == f"task-{task.id}"


def test_assign_workflow_thread(db_session):
    task = Task(
        user_id="test-user",
        request="Investigate payment failures",
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    result = assign_workflow_thread(
        db=db_session,
        task=task,
    )

    assert result.workflow_thread_id == f"task-{task.id}"

    db_session.refresh(task)

    assert task.workflow_thread_id == f"task-{task.id}"


def test_assign_workflow_thread_preserves_existing_thread(db_session):
    task = Task(
        user_id="test-user",
        request="Investigate payment failures",
        workflow_thread_id="existing-thread",
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    result = assign_workflow_thread(
        db=db_session,
        task=task,
    )

    assert result.workflow_thread_id == "existing-thread"


def test_start_task_workflow_assigns_thread_and_completes(db_session):
    plan = AgentPlan(
        reasoning_summary="Investigate payment failures.",
        tool_call={
            "tool": "sql.read",
            "arguments": {
                "query": "SELECT COUNT(*) FROM payment_failures",
            },
        },
    )

    task = Task(
        user_id="user-123",
        request="Investigate payment failures",
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    runner = WorkflowRunner(
        FakeLLMProvider(plan),
        db=db_session,
    )

    result = start_task_workflow(
        db=db_session,
        task=task,
        workflow_runner=runner,
    )

    assert result["status"] == AgentStatus.COMPLETED
    assert result["task_id"] == task.id
    assert result["tool_result"]["tool"] == "sql.read"

    db_session.refresh(task)

    assert task.workflow_thread_id == f"task-{task.id}"