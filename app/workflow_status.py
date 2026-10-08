
from sqlalchemy.orm import Session

from app.agents.state import AgentStatus
from app.models import Task, TaskStatus
from app.task_service import (
    InvalidTaskTransition,
    transition_task,
)
from app.task_service_db import update_task_status


AGENT_TO_TASK_STATUS: dict[AgentStatus, TaskStatus] = {
    AgentStatus.PLANNING: TaskStatus.PLANNING,
    AgentStatus.EXECUTING_TOOL: TaskStatus.EXECUTING,
    AgentStatus.EXECUTING_ACTION: TaskStatus.EXECUTING,
    AgentStatus.AWAITING_APPROVAL: TaskStatus.AWAITING_APPROVAL,
    AgentStatus.VERIFYING: TaskStatus.VERIFYING,
    AgentStatus.COMPLETED: TaskStatus.COMPLETED,
    AgentStatus.FAILED: TaskStatus.FAILED,
}


def can_sync_task_status(
    task: Task,
    agent_status: AgentStatus,
) -> bool:
    target_status = AGENT_TO_TASK_STATUS.get(agent_status)

    if target_status is None:
        return False

    current_status = TaskStatus(task.status)

    if current_status == target_status:
        return True

    try:
        transition_task(
            current_status,
            target_status,
        )
    except InvalidTaskTransition:
        return False

    return True


def sync_task_status(
    db: Session,
    task: Task,
    agent_status: AgentStatus,
    actor: str = "workflow",
) -> Task:
    task_status = AGENT_TO_TASK_STATUS.get(agent_status)

    if task_status is None:
        return task

    current_status = TaskStatus(task.status)

    if current_status == task_status:
        return task

    return update_task_status(
        db=db,
        task=task,
        new_status=task_status,
        actor=actor,
    )

