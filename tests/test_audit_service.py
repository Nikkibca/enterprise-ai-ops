
import pytest
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


def test_record_audit_event_rejects_blank_actor():
    db = SessionLocal()

    try:
        task = Task(
            user_id="test-user",
            request="Audit actor validation test",
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        with pytest.raises(
            ValueError,
            match="actor must be a non-empty string",
        ):
            record_audit_event(
                db=db,
                task_id=task.id,
                event_type="task.created",
                actor="   ",
            )

    finally:
        db.close()


def test_record_audit_event_rejects_blank_event_type():
    db = SessionLocal()

    try:
        task = Task(
            user_id="test-user",
            request="Audit event type validation test",
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        with pytest.raises(
            ValueError,
            match="event type must be a non-empty string",
        ):
            record_audit_event(
                db=db,
                task_id=task.id,
                event_type="   ",
                actor="test-user",
            )

    finally:
        db.close()

def test_record_audit_event_redacts_sensitive_values(
    db_session,
):
    task = Task(
        user_id="test-user",
        request="Audit redaction test",
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    event = record_audit_event(
        db=db_session,
        task_id=task.id,
        event_type="security.test",
        actor="test-user",
        details={
            "username": "operator",
            "password": "super-secret-password",
            "api_key": "secret-api-key",
            "nested": {
                "access_token": "secret-access-token",
                "safe_value": "visible",
            },
            "items": [
                {
                    "client_secret": "nested-secret",
                },
                {
                    "name": "safe",
                },
            ],
        },
    )

    saved_event = db_session.get(
        AuditEvent,
        event.id,
    )

    assert saved_event is not None

    import json

    details = json.loads(saved_event.details)

    assert details == {
        "username": "operator",
        "password": "[REDACTED]",
        "api_key": "[REDACTED]",
        "nested": {
            "access_token": "[REDACTED]",
            "safe_value": "visible",
        },
        "items": [
            {
                "client_secret": "[REDACTED]",
            },
            {
                "name": "safe",
            },
        ],
    }


def test_record_audit_event_redacts_common_secret_key_variants(
    db_session,
):
    task = Task(
        user_id="test-user",
        request="Audit key normalization test",
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    event = record_audit_event(
        db=db_session,
        task_id=task.id,
        event_type="security.test",
        actor="test-user",
        details={
            "Authorization": "Bearer secret",
            "refresh-token": "refresh-secret",
            "service_password": "password-secret",
            "externalApiKey": "api-secret",
            "normal_field": "safe",
        },
    )

    import json

    details = json.loads(event.details)

    assert details["Authorization"] == "[REDACTED]"
    assert details["refresh-token"] == "[REDACTED]"
    assert details["service_password"] == "[REDACTED]"
    assert details["externalApiKey"] == "[REDACTED]"
    assert details["normal_field"] == "safe"


def test_record_audit_event_preserves_non_sensitive_details(
    db_session,
):
    task = Task(
        user_id="test-user",
        request="Audit details preservation test",
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    event = record_audit_event(
        db=db_session,
        task_id=task.id,
        event_type="tool.completed",
        actor="operator",
        details={
            "tool_name": "service.restart",
            "risk_level": "high",
            "approval_id": 123,
            "status": "success",
            "arguments": {
                "service": "payment-worker",
            },
        },
    )

    import json

    assert json.loads(event.details) == {
        "tool_name": "service.restart",
        "risk_level": "high",
        "approval_id": 123,
        "status": "success",
        "arguments": {
            "service": "payment-worker",
        },
    }