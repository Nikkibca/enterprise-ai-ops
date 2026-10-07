from sqlalchemy import select

from app.audit.service import record_audit_event
from app.db import SessionLocal
from app.models import AuditEvent, Task


def test_record_audit_event():
    db = SessionLocal()

    try:
        task = Task(
            user_id="test-user",
            request="Audit integration test",
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        event = record_audit_event(
            db=db,
            task_id=task.id,
            event_type="task.created",
            actor="test",
            details={
                "source": "integration_test",
            },
        )

        assert event.id is not None
        assert event.task_id == task.id
        assert event.event_type == "task.created"
        assert event.actor == "test"

        saved_event = db.scalar(
            select(AuditEvent).where(
                AuditEvent.id == event.id
            )
        )

        assert saved_event is not None
        assert saved_event.task_id == task.id
        assert saved_event.event_type == "task.created"

    finally:
        db.close()
