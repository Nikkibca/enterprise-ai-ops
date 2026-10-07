from sqlalchemy.orm import Session

from app.audit.service import record_audit_event
from app.models import Task, TaskStatus
from app.task_service import transition_task


def update_task_status(
    db: Session,
    task: Task,
    new_status: TaskStatus,
    actor: str = "system",
) -> Task:
    current_status = TaskStatus(task.status)

    validated_status = transition_task(
        current_status,
        new_status,
    )

    task.status = validated_status.value

    record_audit_event(
        db=db,
        task_id=task.id,
        event_type="task.status_changed",
        actor=actor,
        details={
            "from": current_status.value,
            "to": validated_status.value,
        },
        commit=False,
    )

    db.commit()
    db.refresh(task)

    return task
