import re


class SQLValidationError(Exception):
    pass


FORBIDDEN_STATEMENTS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "GRANT",
    "REVOKE",
    "MERGE",
}


def validate_read_only_sql(query: str) -> str:
    if not query or not query.strip():
        raise SQLValidationError(
            "SQL query cannot be empty."
        )

    normalized = query.strip()

    # Remove trailing semicolons so we can inspect the statement cleanly.
    normalized = normalized.rstrip(";").strip()

    # Only a SELECT statement is allowed.
    if not re.match(r"^SELECT\b", normalized, re.IGNORECASE):
        raise SQLValidationError(
            "Only SELECT statements are allowed."
        )

    # Reject multiple statements.
    if ";" in normalized:
        raise SQLValidationError(
            "Multiple SQL statements are not allowed."
        )

    # Reject explicitly dangerous SQL keywords.
    for statement in FORBIDDEN_STATEMENTS:
        if re.search(
            rf"\b{statement}\b",
            normalized,
            re.IGNORECASE,
        ):
            raise SQLValidationError(
                f"SQL statement not allowed: {statement}"
            )

    return normalized