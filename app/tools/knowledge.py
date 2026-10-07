from typing import Any


def knowledge_search(
    arguments: dict[str, Any],
) -> dict[str, Any]:
    query = arguments.get("query")

    if not query:
        raise ValueError(
            "knowledge.search requires a query."
        )

    return {
        "tool": "knowledge.search",
        "status": "simulated",
        "query": query,
        "results": [
            {
                "title": "Payment Timeout Troubleshooting",
                "content": (
                    "Check payment worker health, database "
                    "latency, upstream payment provider errors, "
                    "and recent deployments."
                ),
            }
        ],
    }