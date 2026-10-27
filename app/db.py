from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class DatabaseSettings(BaseSettings):
    app_database_url: str = (
        "postgresql+psycopg://app_user:app_password@127.0.0.1:5433/enterprise_ai_ops"
    )
    sql_reader_database_url: str = (
        "postgresql+psycopg://sql_reader:sql_reader_password@127.0.0.1:5433/enterprise_ai_ops"
    )

    @field_validator("app_database_url", "sql_reader_database_url", mode="before")
    @classmethod
    def normalize_db_url(cls, value: str) -> str:
        if isinstance(value, str):
            # Normalize localhost:5433 to 127.0.0.1:5433 to prevent 120s IPv6 timeouts on Windows
            return value.replace("@localhost:5433", "@127.0.0.1:5433")
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


_db_settings = DatabaseSettings()

DATABASE_URL = _db_settings.app_database_url
SQL_READER_DATABASE_URL = _db_settings.sql_reader_database_url


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
