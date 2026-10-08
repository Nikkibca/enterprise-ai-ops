import pytest

from app.tools.knowledge import knowledge_search


class FakeKnowledgeClient:
    def __init__(self):
        self.calls = []

    def search(self, *, query, top_k):
        self.calls.append(
            {
                "query": query,
                "top_k": top_k,
            }
        )

        return {
            "query": query,
            "results": [
                {
                    "content": "Restart the payment worker.",
                }
            ],
        }


def test_knowledge_search_delegates_to_project1_client(
    monkeypatch,
):
    fake_client = FakeKnowledgeClient()

    monkeypatch.setattr(
        "app.tools.knowledge.Project1KnowledgeClient",
        lambda: fake_client,
    )

    result = knowledge_search(
        {
            "query": "payment timeout",
            "top_k": 7,
        }
    )

    assert fake_client.calls == [
        {
            "query": "payment timeout",
            "top_k": 7,
        }
    ]

    assert result == {
        "tool": "knowledge.search",
        "status": "success",
        "query": "payment timeout",
        "results": [
            {
                "content": "Restart the payment worker.",
            }
        ],
    }


def test_knowledge_search_uses_default_top_k(
    monkeypatch,
):
    fake_client = FakeKnowledgeClient()

    monkeypatch.setattr(
        "app.tools.knowledge.Project1KnowledgeClient",
        lambda: fake_client,
    )

    knowledge_search(
        {
            "query": "payment timeout",
        }
    )

    assert fake_client.calls == [
        {
            "query": "payment timeout",
            "top_k": 5,
        }
    ]


@pytest.mark.parametrize(
    "arguments, expected_message",
    [
        (
            {},
            "knowledge.search requires a query.",
        ),
        (
            {
                "query": "",
            },
            "knowledge.search requires a query.",
        ),
        (
            {
                "query": "payment timeout",
                "top_k": "5",
            },
            "knowledge.search top_k must be an integer.",
        ),
        (
            {
                "query": "payment timeout",
                "top_k": 0,
            },
            (
                "knowledge.search top_k must be "
                "between 1 and 20."
            ),
        ),
        (
            {
                "query": "payment timeout",
                "top_k": 21,
            },
            (
                "knowledge.search top_k must be "
                "between 1 and 20."
            ),
        ),
    ],
)
def test_knowledge_search_validates_arguments(
    arguments,
    expected_message,
):
    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        knowledge_search(arguments)