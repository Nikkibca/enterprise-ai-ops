from sqlalchemy import select

from app.db import SessionLocal
from app.models import AuditEvent, Task, TaskStatus
from app.task_service_db import update_task_status


def test_update_task_status_creates_audit_event():
    db = SessionLocal()

    try:
        task = Task(
            user_id="test-user",
            request="Test audited transition",
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        updated_task = update_task_status(
            db,
            task,
            TaskStatus.PLANNING,
            actor="test-agent",
        )

        assert updated_task.status == TaskStatus.PLANNING

        audit_event = db.scalar(
            select(AuditEvent)
            .where(AuditEvent.task_id == task.id)
            .where(AuditEvent.event_type == "task.status_changed")
            .order_by(AuditEvent.id.desc())
        )

        assert audit_event is not None
        assert audit_event.actor == "test-agent"
        assert '"from": "created"' in audit_event.details
        assert '"to": "planning"' in audit_event.details

    finally:
        db.close()


def test_update_task_status_rolls_back_when_audit_fails():
    db = SessionLocal()

    try:
        task = Task(
            user_id="test-user",
            request="Test rollback behavior",
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        original_status = task.status

        def failing_audit(*args, **kwargs):
            raise RuntimeError("Simulated audit failure")

        import app.task_service_db as task_service_db

        original_audit = task_service_db.record_audit_event
        task_service_db.record_audit_event = failing_audit

        try:
            try:
                update_task_status(
                    db,
                    task,
                    TaskStatus.PLANNING,
                    actor="test-agent",
                )
            except RuntimeError:
                pass
        finally:
            task_service_db.record_audit_event = original_audit

        db.rollback()
        db.refresh(task)

        assert task.status == original_status

    finally:
        db.close()
