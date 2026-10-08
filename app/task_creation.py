
from sqlalchemy.orm import Session

from app.audit.service import record_audit_event
from app.models import Task


def create_task(
    db: Session,
    user_id: str,
    request: str,
    actor: str,
) -> Task:
    task = Task(
        user_id=user_id,
        request=request,
    )

    db.add(task)
    db.flush()

    record_audit_event(
        db=db,
        task_id=task.id,
        event_type="task.created",
        actor=actor,
        details={
            "user_id": user_id,
        },
        commit=False,
    )

    db.commit()
    db.refresh(task)

    return task

