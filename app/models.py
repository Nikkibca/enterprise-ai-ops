from datetime import datetime, timezone
from enum import Enum
import json

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    TypeDecorator,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class JSONText(TypeDecorator):
    """
    SQLAlchemy type decorator that persists JSON data as PostgreSQL JSON
    while providing transparent string/JSON serialization in Python.

    - Preserves SQL NULL as None.
    - Serializes all JSON data structures (objects, arrays, strings, numbers, booleans)
      consistently as valid JSON strings in Python (via json.dumps).
    - Preserves all legitimate JSON objects (including keys like '_raw'
      or '__legacy_unstructured_text__') without lossy sentinel unwrapping.
    - Legacy unquoted text and empty strings are stored as JSON string values,
      ensuring callers executing json.loads(event.details) always succeed.
    - Ensures PostgreSQL native JSON operators (e.g. details->>'success') work in SQL.
    """
    impl = JSON
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                return value
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)


class Base(DeclarativeBase):
    pass


class TaskStatus(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    request: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=TaskStatus.CREATED.value,
    )

    workflow_thread_id: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        unique=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    tool_arguments: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id"),
        nullable=False,
        index=True,
    )

    tool_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    risk_level: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    requested_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ApprovalStatus.PENDING.value,
    )

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    decided_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    execution_claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    execution_claimed_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id"),
        nullable=False,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    actor: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    details: Mapped[str] = mapped_column(
        JSONText,
        nullable=False,
        default="",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    amount: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    provider: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class PaymentFailure(Base):
    __tablename__ = "payment_failures"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    payment_id: Mapped[int] = mapped_column(
        ForeignKey("payments.id"),
        nullable=False,
    )

    error_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    error_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    provider: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )