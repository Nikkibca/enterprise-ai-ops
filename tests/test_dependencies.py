
from app.dependencies import get_llm_provider
from app.llm.openai_provider import OpenAIProvider


def test_get_llm_provider_returns_openai_provider():
    provider = get_llm_provider()

    assert isinstance(provider, OpenAIProvider)

