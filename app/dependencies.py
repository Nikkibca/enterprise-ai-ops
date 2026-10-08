from collections.abc import Generator

from fastapi import Request
from langgraph.checkpoint.base import BaseCheckpointSaver
from sqlalchemy.orm import Session

from app.agents.schemas import AgentPlan, ToolCall
from app.db import SessionLocal
from app.llm.base import LLMProvider
from app.llm.fake import FakeLLMProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.settings import LLMSettings


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def get_llm_provider() -> LLMProvider:
    settings = LLMSettings()

    if settings.llm_provider.lower() == "fake":
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

    return OpenAIProvider(settings)


def get_checkpointer(
    request: Request,
) -> BaseCheckpointSaver:
    return request.app.state.checkpointer