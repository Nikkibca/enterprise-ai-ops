import json
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditEvent


SENSITIVE_KEY_NAMES = {
    "access_token",
    "api_key",
    "apikey",
    "authorization",
    "client_secret",
    "credential",
    "credentials",
    "id_token",
    "password",
    "private_key",
    "refresh_token",
    "secret",
    "token",
}


def _normalize_key(key: str) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        key.lower(),
    ).strip("_")


def _is_sensitive_key(key: str) -> bool:
    normalized = _normalize_key(key)
    compact = normalized.replace("_", "")

    if normalized in SENSITIVE_KEY_NAMES:
        return True

    if compact in {
        "apikey",
        "accesstoken",
        "refreshtoken",
        "idtoken",
        "clientsecret",
        "privatedkey",
        "password",
        "authorization",
        "credential",
        "credentials",
    }:
        return True

    return (
        normalized.endswith("_token")
        or normalized.endswith("_secret")
        or normalized.endswith("_password")
        or normalized.endswith("_api_key")
        or compact.endswith("token")
        or compact.endswith("secret")
        or compact.endswith("password")
        or compact.endswith("apikey")
    )


def _sanitize_audit_details(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized = {}

        for key, item in value.items():
            if isinstance(key, str) and _is_sensitive_key(key):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = _sanitize_audit_details(item)

        return sanitized

    if isinstance(value, list):
        return [
            _sanitize_audit_details(item)
            for item in value
        ]

    if isinstance(value, tuple):
        return [
            _sanitize_audit_details(item)
            for item in value
        ]

    return value


def record_audit_event(
    db: Session,
    task_id: int,
    event_type: str,
    actor: str,
    details: dict | None = None,
    commit: bool = True,
) -> AuditEvent:
    if not isinstance(actor, str) or not actor.strip():
        raise ValueError(
            "Audit event actor must be a non-empty string."
        )

    if not isinstance(event_type, str) or not event_type.strip():
        raise ValueError(
            "Audit event type must be a non-empty string."
        )

    sanitized_details = _sanitize_audit_details(
        details or {},
    )

    event = AuditEvent(
        task_id=task_id,
        event_type=event_type.strip(),
        actor=actor.strip(),
        details=json.dumps(sanitized_details),
    )

    db.add(event)

    if commit:
        db.commit()
        db.refresh(event)

    return event