from pathlib import Path
import sys

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db import engine


def main() -> None:
    sql = """
    ALTER TABLE approval_requests
        ADD COLUMN IF NOT EXISTS execution_claimed_at
            TIMESTAMPTZ NULL,
        ADD COLUMN IF NOT EXISTS execution_claimed_by
            VARCHAR(100) NULL;
    """

    with engine.begin() as connection:
        connection.execute(text(sql))

    print(
        "Ensured approval execution-claim columns exist."
    )


if __name__ == "__main__":
    main()