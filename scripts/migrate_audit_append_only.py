from pathlib import Path
import sys

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db import engine


FUNCTION_NAME = "prevent_audit_event_mutation"
TRIGGER_NAME = "trg_audit_events_append_only"


def main() -> None:
    sql = f"""
    CREATE OR REPLACE FUNCTION {FUNCTION_NAME}()
    RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
        RAISE EXCEPTION
            'audit_events are append-only and cannot be updated or deleted';
    END;
    $$;

    DROP TRIGGER IF EXISTS {TRIGGER_NAME}
    ON audit_events;

    CREATE TRIGGER {TRIGGER_NAME}
    BEFORE UPDATE OR DELETE
    ON audit_events
    FOR EACH ROW
    EXECUTE FUNCTION {FUNCTION_NAME}();
    """

    with engine.begin() as connection:
        connection.execute(text(sql))

    print(
        "Ensured audit_events append-only trigger exists: "
        f"{TRIGGER_NAME}"
    )


if __name__ == "__main__":
    main()