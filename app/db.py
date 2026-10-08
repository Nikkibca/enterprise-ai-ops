import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


DATABASE_URL = os.getenv(
    "APP_DATABASE_URL",
    "postgresql+psycopg://app_user:app_password@localhost:5433/enterprise_ai_ops",
)

SQL_READER_DATABASE_URL = os.getenv(
    "SQL_READER_DATABASE_URL",
    "postgresql+psycopg://sql_reader:sql_reader_password@localhost:5433/enterprise_ai_ops",
)


# Main application database connection.
# Used for normal application operations such as tasks,
# audit events, seeding, and migrations.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


# Dedicated read-only connection.
# The PostgreSQL role behind this connection has SELECT-only
# permissions on the operational tables.
sql_reader_engine = create_engine(
    SQL_READER_DATABASE_URL,
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)
