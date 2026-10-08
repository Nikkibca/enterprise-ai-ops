
from sqlalchemy.orm import Session

from app.agents.state import AgentState
from app.models import Task
from app.workflow_runner import WorkflowRunner
from app.agents.limits import (
    DEFAULT_MAX_INVESTIGATION_STEPS,
)


def build_workflow_thread_id(task: Task) -> str:
    return f"task-{task.id}"


def assign_workflow_thread(
    db: Session,
    task: Task,
) -> Task:
    if task.workflow_thread_id:
        return task

    task.workflow_thread_id = build_workflow_thread_id(task)

    db.commit()
    db.refresh(task)

    return task


def start_task_workflow(
    db: Session,
    task: Task,
    workflow_runner: WorkflowRunner,
) -> AgentState:
    task = assign_workflow_thread(
        db=db,
        task=task,
    )

    initial_state: AgentState = {
        "task_id": task.id,
        "user_id": task.user_id,
        "request": task.request,
        "investigation_step": 0,
        "max_investigation_steps": (
            DEFAULT_MAX_INVESTIGATION_STEPS
        ),
    }

    return workflow_runner.start(
        initial_state,
        thread_id=task.workflow_thread_id,
    )

