from sqlalchemy import select

from app.db import SessionLocal
from app.models import AuditEvent
from app.task_creation import create_task


def test_create_task_creates_audit_event():
    db = SessionLocal()

    try:
        task = create_task(
            db=db,
            user_id="test-user",
            request="Create task audit test",
            actor="test-user",
        )

        assert task.id is not None
        assert task.status == "created"

        audit_event = db.scalar(
            select(AuditEvent)
            .where(AuditEvent.task_id == task.id)
            .where(AuditEvent.event_type == "task.created")
        )

        assert audit_event is not None
        assert audit_event.actor == "test-user"
        assert '"user_id": "test-user"' in audit_event.details

    finally:
        db.close()
