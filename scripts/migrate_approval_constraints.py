from pathlib import Path
import sys

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db import engine


INDEX_NAME = "ux_approval_requests_pending_task_tool"


def main() -> None:
    sql = f"""
    CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME}
    ON approval_requests (task_id, tool_name)
    WHERE status = 'pending';
    """

    with engine.begin() as connection:
        connection.execute(text(sql))

    print(f"Ensured PostgreSQL index exists: {INDEX_NAME}")


if __name__ == "__main__":
    main()
