import json

from sqlalchemy.orm import Session

from app.models import AuditEvent


def record_audit_event(
    db: Session,
    task_id: int,
    event_type: str,
    actor: str,
    details: dict | None = None,
    commit: bool = True,
) -> AuditEvent:
    event = AuditEvent(
        task_id=task_id,
        event_type=event_type,
        actor=actor,
        details=json.dumps(details or {}),
    )

    db.add(event)

    if commit:
        db.commit()
        db.refresh(event)

    return event
