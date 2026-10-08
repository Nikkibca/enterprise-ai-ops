import json

import httpx

from app.rag.project1_client import Project1KnowledgeClient


def test_project1_client_search():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == (
            "http://project1.test/search"
        )

        assert json.loads(request.content) == {
            "query": "payment timeout",
            "top_k": 3,
        }

        return httpx.Response(
            status_code=200,
            json={
                "query": "payment timeout",
                "results": [
                    {
                        "document_id": 1,
                        "filename": "payments.md",
                        "chunk_id": 10,
                        "chunk_index": 0,
                        "content": (
                            "Payment timeout troubleshooting."
                        ),
                        "distance": 0.12,
                        "metadata": {
                            "source": "payments.md",
                            "chunk_index": 0,
                        },
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)

    client = Project1KnowledgeClient(
        base_url="http://project1.test",
    )

    original_post = httpx.post

    try:
        httpx.post = lambda *args, **kwargs: httpx.Client(
            transport=transport
        ).post(*args, **kwargs)

        result = client.search(
            query="payment timeout",
            top_k=3,
        )

    finally:
        httpx.post = original_post

    assert result["query"] == "payment timeout"
    assert len(result["results"]) == 1
    assert result["results"][0]["filename"] == "payments.md"


def test_project1_client_raises_for_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=503,
            json={
                "detail": "Search service is temporarily unavailable"
            },
        )

    transport = httpx.MockTransport(handler)

    client = Project1KnowledgeClient(
        base_url="http://project1.test",
    )

    original_post = httpx.post

    try:
        httpx.post = lambda *args, **kwargs: httpx.Client(
            transport=transport
        ).post(*args, **kwargs)

        try:
            client.search(
                query="payment timeout",
                top_k=3,
            )
            raise AssertionError(
                "Expected HTTPStatusError"
            )

        except httpx.HTTPStatusError as exc:
            assert exc.response.status_code == 503

    finally:
        httpx.post = original_post    