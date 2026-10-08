import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.models import AuditEvent, Task


def create_task(db_session):
    task = Task(
        user_id="audit-test-user",
        request="Audit integrity test",
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


def create_audit_event(db_session, task):
    event = AuditEvent(
        task_id=task.id,
        event_type="test.event",
        actor="test-user",
        details='{"source": "integrity_test"}',
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event


def test_audit_event_can_be_inserted(db_session):
    task = create_task(db_session)

    event = create_audit_event(
        db_session,
        task,
    )

    saved_event = db_session.scalar(
        select(AuditEvent).where(
            AuditEvent.id == event.id,
        )
    )

    assert saved_event is not None
    assert saved_event.event_type == "test.event"


def test_audit_event_cannot_be_updated(db_session):
    task = create_task(db_session)
    event = create_audit_event(
        db_session,
        task,
    )

    with pytest.raises(DBAPIError, match="append-only"):
        db_session.execute(
            text(
                """
                UPDATE audit_events
                SET actor = 'tampered-user'
                WHERE id = :event_id
                """
            ),
            {"event_id": event.id},
        )
        db_session.commit()

    db_session.rollback()

    saved_event = db_session.scalar(
        select(AuditEvent).where(
            AuditEvent.id == event.id,
        )
    )

    assert saved_event is not None
    assert saved_event.actor == "test-user"


def test_audit_event_cannot_be_deleted(db_session):
    task = create_task(db_session)
    event = create_audit_event(
        db_session,
        task,
    )

    with pytest.raises(DBAPIError, match="append-only"):
        db_session.execute(
            text(
                """
                DELETE FROM audit_events
                WHERE id = :event_id
                """
            ),
            {"event_id": event.id},
        )
        db_session.commit()

    db_session.rollback()

    saved_event = db_session.scalar(
        select(AuditEvent).where(
            AuditEvent.id == event.id,
        )
    )

    assert saved_event is not None