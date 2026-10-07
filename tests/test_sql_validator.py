import pytest

from app.tools.sql_validator import (
    SQLValidationError,
    validate_read_only_sql,
)


def test_select_query_is_allowed():
    query = "SELECT COUNT(*) FROM payment_failures"

    result = validate_read_only_sql(query)

    assert result == query


def test_select_query_with_trailing_semicolon_is_allowed():
    query = "SELECT COUNT(*) FROM payment_failures;"

    result = validate_read_only_sql(query)

    assert result == (
        "SELECT COUNT(*) FROM payment_failures"
    )


@pytest.mark.parametrize(
    "query",
    [
        "INSERT INTO payments VALUES (1)",
        "UPDATE payments SET status = 'failed'",
        "DELETE FROM payments",
        "DROP TABLE payments",
        "ALTER TABLE payments ADD COLUMN test TEXT",
        "TRUNCATE TABLE payments",
        "CREATE TABLE test (id INT)",
        "GRANT SELECT ON payments TO app_user",
        "REVOKE SELECT ON payments FROM app_user",
        "MERGE INTO payments USING other_table ON true",
    ],
)
def test_write_or_ddl_statements_are_rejected(query):
    with pytest.raises(SQLValidationError):
        validate_read_only_sql(query)


def test_empty_query_is_rejected():
    with pytest.raises(SQLValidationError):
        validate_read_only_sql("")


def test_whitespace_query_is_rejected():
    with pytest.raises(SQLValidationError):
        validate_read_only_sql("   ")


@pytest.mark.parametrize(
    "query",
    [
        "UPDATE payments SET status = 'failed'; SELECT 1",
        "SELECT 1; DELETE FROM payments",
        "SELECT 1; SELECT 2",
    ],
)
def test_multiple_statements_are_rejected(query):
    with pytest.raises(SQLValidationError):
        validate_read_only_sql(query)


def test_non_select_statement_is_rejected():
    with pytest.raises(SQLValidationError):
        validate_read_only_sql(
            "EXPLAIN SELECT * FROM payments"
        )


def test_select_is_case_insensitive():
    query = "select count(*) from payments"

    result = validate_read_only_sql(query)

    assert result == query