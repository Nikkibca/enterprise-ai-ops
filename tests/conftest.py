import pytest
from sqlalchemy import text

from app.db import SessionLocal


@pytest.fixture
def db_session():
    db = SessionLocal()

    def clean_database():
        db.rollback()

        db.execute(
            text(
                """
                TRUNCATE TABLE
                    approval_requests,
                    audit_events,
                    tasks
                RESTART IDENTITY
                """
            )
        )

        db.commit()

    try:
        # Clean test data before the test.
        clean_database()

        yield db

    finally:
        # Clean test data after the test.
        clean_database()
        db.close()