from pathlib import Path
import sys

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db import engine


def main() -> None:
    """Safely migrate audit_events.details from text to json if not already migrated.

    Preserves all existing audit records:
    - SQL NULL remains SQL NULL.
    - Valid JSON values (objects, arrays, strings, numbers, booleans) become native JSON.
    - Non-JSON legacy text and empty strings are preserved as valid JSON string values via to_json(val).
    """
    check_type_sql = """
    SELECT data_type
    FROM information_schema.columns
    WHERE table_name = 'audit_events' AND column_name = 'details';
    """

    create_func_sql = """
    CREATE OR REPLACE FUNCTION convert_audit_details_to_json(val text)
    RETURNS json
    LANGUAGE plpgsql
    IMMUTABLE
    AS $$
    BEGIN
        IF val IS NULL THEN
            RETURN NULL;
        END IF;

        BEGIN
            RETURN val::json;
        EXCEPTION WHEN others THEN
            RETURN to_json(val);
        END;
    END;
    $$;
    """

    alter_table_sql = """
    ALTER TABLE audit_events
        ALTER COLUMN details TYPE JSON
        USING convert_audit_details_to_json(details);
    """

    drop_func_sql = """
    DROP FUNCTION IF EXISTS convert_audit_details_to_json(text);
    """

    with engine.begin() as connection:
        current_type = connection.execute(text(check_type_sql)).scalar()
        if current_type and current_type.lower() in ("text", "character varying"):
            try:
                connection.execute(text(create_func_sql))
                connection.execute(text(alter_table_sql))
            finally:
                try:
                    connection.execute(text(drop_func_sql))
                except Exception:
                    # If the transaction was aborted due to an ALTER TABLE failure,
                    # PostgreSQL transactional DDL rolls back the CREATE FUNCTION
                    # statement along with the entire transaction.
                    pass
            print("Migrated audit_events.details column to JSON.")
        else:
            print(f"audit_events.details is already type '{current_type}'. No migration needed.")


if __name__ == "__main__":
    main()
