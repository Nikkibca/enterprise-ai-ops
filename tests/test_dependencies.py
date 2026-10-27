import pytest

from app.dependencies import LLMConfigurationError, get_llm_provider
from app.llm.fake import FakeLLMProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.settings import LLMSettings


def test_get_llm_provider_returns_openai_provider():
    settings = LLMSettings(
        llm_provider="openai",
        openai_api_key="test-api-key",
        openai_model="gpt-4o",
    )
    provider = get_llm_provider(settings)

    assert isinstance(provider, OpenAIProvider)
    assert provider.settings.openai_model == "gpt-4o"


def test_get_llm_provider_returns_fake_provider():
    settings = LLMSettings(
        llm_provider="fake",
    )
    provider = get_llm_provider(settings)

    assert isinstance(provider, FakeLLMProvider)


def test_get_llm_provider_fails_safely_when_openai_key_missing():
    settings = LLMSettings(
        llm_provider="openai",
        openai_api_key="",
        openai_model="gpt-4o",
    )
    with pytest.raises(LLMConfigurationError, match="OPENAI_API_KEY is not set or empty"):
        get_llm_provider(settings)


def test_get_llm_provider_fails_safely_when_openai_model_missing():
    settings = LLMSettings(
        llm_provider="openai",
        openai_api_key="test-key",
        openai_model="",
    )
    with pytest.raises(LLMConfigurationError, match="OPENAI_MODEL is not set or empty"):
        get_llm_provider(settings)


def test_get_llm_provider_fails_safely_for_unsupported_provider():
    settings = LLMSettings(
        llm_provider="unsupported_custom_llm",
    )
    with pytest.raises(LLMConfigurationError, match="Unsupported LLM provider"):
        get_llm_provider(settings)


def test_get_llm_provider_uses_default_settings_without_error():
    provider = get_llm_provider()
    assert isinstance(provider, (FakeLLMProvider, OpenAIProvider))
