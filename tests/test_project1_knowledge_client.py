import httpx
import pytest

from app.rag.project1_client import Project1KnowledgeClient


def test_project1_client_sends_search_request(monkeypatch):
    captured = {}

    def fake_post(url, *, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout

        return httpx.Response(
            status_code=200,
            json={
                "query": "payment timeout",
                "results": [
                    {
                        "content": "Restart the payment worker.",
                    }
                ],
            },
            request=httpx.Request(
                "POST",
                url,
            ),
        )

    monkeypatch.setattr(
        "app.rag.project1_client.httpx.post",
        fake_post,
    )

    client = Project1KnowledgeClient(
        base_url="http://project1:8000",
        timeout=15.0,
    )

    result = client.search(
        query="payment timeout",
        top_k=7,
    )

    assert captured["url"] == (
        "http://project1:8000/search"
    )

    assert captured["json"] == {
        "query": "payment timeout",
        "top_k": 7,
    }

    assert captured["timeout"] == 15.0

    assert result == {
        "query": "payment timeout",
        "results": [
            {
                "content": "Restart the payment worker.",
            }
        ],
    }


def test_project1_client_strips_trailing_slash(monkeypatch):
    captured = {}

    def fake_post(url, *, json, timeout):
        captured["url"] = url

        return httpx.Response(
            status_code=200,
            json={"results": []},
            request=httpx.Request(
                "POST",
                url,
            ),
        )

    monkeypatch.setattr(
        "app.rag.project1_client.httpx.post",
        fake_post,
    )

    client = Project1KnowledgeClient(
        base_url="http://project1:8000///",
    )

    client.search("payment failures")

    assert captured["url"] == (
        "http://project1:8000/search"
    )


def test_project1_client_raises_for_http_error(monkeypatch):
    def fake_post(url, *, json, timeout):
        return httpx.Response(
            status_code=500,
            json={
                "detail": "Knowledge service unavailable.",
            },
            request=httpx.Request(
                "POST",
                url,
            ),
        )

    monkeypatch.setattr(
        "app.rag.project1_client.httpx.post",
        fake_post,
    )

    client = Project1KnowledgeClient(
        base_url="http://project1:8000",
    )

    with pytest.raises(httpx.HTTPStatusError):
        client.search("payment failures")