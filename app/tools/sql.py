from typing import Any

from sqlalchemy import text

from app.db import sql_reader_engine
from app.tools.sql_validator import validate_read_only_sql


def sql_read(arguments: dict[str, Any]) -> dict[str, Any]:
    query = arguments.get("query")

    if not query:
        raise ValueError("sql.read requires a query.")

    validated_query = validate_read_only_sql(query)

    with sql_reader_engine.connect() as connection:
        result = connection.execute(text(validated_query))

        rows = [
            dict(row)
            for row in result.mappings().all()
        ]

    return {
        "tool": "sql.read",
        "status": "success",
        "query": validated_query,
        "row_count": len(rows),
        "rows": rows,
    }