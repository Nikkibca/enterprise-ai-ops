from collections.abc import Generator

from fastapi import Depends, Request
from langgraph.checkpoint.base import BaseCheckpointSaver
from sqlalchemy.orm import Session

from app.agents.schemas import AgentPlan, ToolCall
from app.db import SessionLocal
from app.llm.base import LLMProvider
from app.llm.fake import FakeLLMProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.settings import LLMSettings


class LLMConfigurationError(ValueError):
    """Raised when the LLM provider configuration is invalid or missing required credentials."""
    pass


def get_llm_settings() -> LLMSettings:
    return LLMSettings()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def get_llm_provider(
    settings: LLMSettings = Depends(get_llm_settings),
) -> LLMProvider:
    if not isinstance(settings, LLMSettings):
        settings = get_llm_settings()

    provider_name = (settings.llm_provider or "").strip().lower()

    if provider_name == "fake":
        plan = AgentPlan(
            reasoning_summary=(
                "Restarting the payment worker is the appropriate "
                "operational action for the requested service."
            ),
            tool_call=ToolCall(
                tool="service.restart",
                arguments={
                    "service": "payment-worker",
                },
            ),
        )

        return FakeLLMProvider(plan)

    if provider_name == "openai":
        if not settings.openai_api_key or not settings.openai_api_key.strip():
            raise LLMConfigurationError(
                "OpenAI LLM provider is configured, but OPENAI_API_KEY is not set or empty."
            )
        if not settings.openai_model or not settings.openai_model.strip():
            raise LLMConfigurationError(
                "OpenAI LLM provider is configured, but OPENAI_MODEL is not set or empty."
            )
        return OpenAIProvider(settings)

    raise LLMConfigurationError(
        f"Unsupported LLM provider: '{settings.llm_provider}'. Supported providers are: 'fake', 'openai'."
    )


def get_checkpointer(
    request: Request,
) -> BaseCheckpointSaver:
    return request.app.state.checkpointer