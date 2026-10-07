import pytest

from app.tools.python_analysis import python_analysis


def test_python_analysis_summary():
    result = python_analysis(
        {
            "operation": "summary",
            "values": [2, 4, 6, 8],
        }
    )

    assert result["tool"] == "python.analysis"
    assert result["status"] == "success"
    assert result["operation"] == "summary"
    assert result["count"] == 4
    assert result["sum"] == 20
    assert result["average"] == 5
    assert result["minimum"] == 2
    assert result["maximum"] == 8


def test_python_analysis_percentage_change():
    result = python_analysis(
        {
            "operation": "percentage_change",
            "values": [100, 125],
        }
    )

    assert result["tool"] == "python.analysis"
    assert result["status"] == "success"
    assert result["percentage_change"] == 25


def test_python_analysis_requires_operation():
    with pytest.raises(
        ValueError,
        match="requires an operation",
    ):
        python_analysis(
            {
                "values": [1, 2, 3],
            }
        )


def test_python_analysis_requires_values():
    with pytest.raises(
        ValueError,
        match="requires a values list",
    ):
        python_analysis(
            {
                "operation": "summary",
            }
        )


def test_python_analysis_rejects_empty_values():
    with pytest.raises(
        ValueError,
        match="at least one value",
    ):
        python_analysis(
            {
                "operation": "summary",
                "values": [],
            }
        )


def test_python_analysis_rejects_non_numeric_values():
    with pytest.raises(
        ValueError,
        match="only numbers",
    ):
        python_analysis(
            {
                "operation": "summary",
                "values": [1, "two", 3],
            }
        )


def test_python_analysis_percentage_change_requires_two_values():
    with pytest.raises(
        ValueError,
        match="exactly two values",
    ):
        python_analysis(
            {
                "operation": "percentage_change",
                "values": [100],
            }
        )


def test_python_analysis_percentage_change_rejects_zero_baseline():
    with pytest.raises(
        ValueError,
        match="cannot use zero",
    ):
        python_analysis(
            {
                "operation": "percentage_change",
                "values": [0, 100],
            }
        )


def test_python_analysis_rejects_unknown_operation():
    with pytest.raises(
        ValueError,
        match="Unsupported",
    ):
        python_analysis(
            {
                "operation": "median",
                "values": [1, 2, 3],
            }
        )