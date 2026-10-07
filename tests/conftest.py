import pytest
from sqlalchemy import delete

from app.db import SessionLocal
from app.models import ApprovalRequest, AuditEvent, Task


@pytest.fixture
def db_session():
    db = SessionLocal()

    try:
        # Clean test data before the test.
        db.execute(delete(ApprovalRequest))
        db.execute(delete(AuditEvent))
        db.execute(delete(Task))
        db.commit()

        yield db

    finally:
        # Clean test data after the test.
        db.execute(delete(ApprovalRequest))
        db.execute(delete(AuditEvent))
        db.execute(delete(Task))
        db.commit()
        db.close()