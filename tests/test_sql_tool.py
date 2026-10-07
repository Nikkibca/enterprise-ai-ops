import pytest

from app.tools.sql import sql_read
from app.tools.sql_validator import SQLValidationError


def test_sql_read_executes_real_query():
    result = sql_read(
        {
            "query": (
                "SELECT COUNT(*) AS payment_count "
                "FROM payments"
            )
        }
    )

    assert result["tool"] == "sql.read"
    assert result["status"] == "success"
    assert result["row_count"] == 1
    assert result["rows"][0]["payment_count"] == 10


def test_sql_read_can_analyze_failures():
    result = sql_read(
        {
            "query": (
                "SELECT error_code, COUNT(*) AS failures "
                "FROM payment_failures "
                "GROUP BY error_code "
                "ORDER BY failures DESC"
            )
        }
    )

    assert result["status"] == "success"
    assert result["row_count"] == 2

    rows = result["rows"]

    assert rows[0]["error_code"] == "PAYMENT_TIMEOUT"
    assert rows[0]["failures"] == 4

    assert rows[1]["error_code"] == "PROVIDER_ERROR"
    assert rows[1]["failures"] == 2


def test_sql_read_rejects_update():
    with pytest.raises(SQLValidationError):
        sql_read(
            {
                "query": (
                    "UPDATE payments "
                    "SET status = 'success'"
                )
            }
        )


def test_sql_read_rejects_delete():
    with pytest.raises(SQLValidationError):
        sql_read(
            {
                "query": "DELETE FROM payments"
            }
        )


def test_sql_read_requires_query():
    with pytest.raises(ValueError):
        sql_read({})