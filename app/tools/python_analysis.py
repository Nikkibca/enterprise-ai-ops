from typing import Any


def python_analysis(
    arguments: dict[str, Any],
) -> dict[str, Any]:
    operation = arguments.get("operation")
    values = arguments.get("values")

    if not operation:
        raise ValueError(
            "python.analysis requires an operation."
        )

    if not isinstance(values, list):
        raise ValueError(
            "python.analysis requires a values list."
        )

    if not values:
        raise ValueError(
            "python.analysis requires at least one value."
        )

    if not all(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        for value in values
    ):
        raise ValueError(
            "python.analysis values must contain only numbers."
        )

    if operation == "summary":
        total = sum(values)
        count = len(values)
        average = total / count

        return {
            "tool": "python.analysis",
            "status": "success",
            "operation": "summary",
            "count": count,
            "sum": total,
            "average": average,
            "minimum": min(values),
            "maximum": max(values),
        }

    if operation == "percentage_change":
        if len(values) != 2:
            raise ValueError(
                "percentage_change requires exactly two values."
            )

        previous, current = values

        if previous == 0:
            raise ValueError(
                "percentage_change cannot use zero as the previous value."
            )

        percentage_change = (
            (current - previous) / previous
        ) * 100

        return {
            "tool": "python.analysis",
            "status": "success",
            "operation": "percentage_change",
            "previous": previous,
            "current": current,
            "percentage_change": percentage_change,
        }

    raise ValueError(
        f"Unsupported python.analysis operation: {operation}"
    )