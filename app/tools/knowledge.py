from typing import Any

from app.rag.project1_client import Project1KnowledgeClient


def knowledge_search(
    arguments: dict[str, Any],
) -> dict[str, Any]:
    query = arguments.get("query")

    if not query:
        raise ValueError(
            "knowledge.search requires a query."
        )

    top_k = arguments.get("top_k", 5)

    if not isinstance(top_k, int):
        raise ValueError(
            "knowledge.search top_k must be an integer."
        )

    if top_k < 1 or top_k > 20:
        raise ValueError(
            "knowledge.search top_k must be between 1 and 20."
        )

    client = Project1KnowledgeClient()

    response = client.search(
        query=query,
        top_k=top_k,
    )

    return {
        "tool": "knowledge.search",
        "status": "success",
        "query": response["query"],
        "results": response["results"],
    }