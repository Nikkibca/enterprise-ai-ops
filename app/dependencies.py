from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.db import SessionLocal
from app.llm.base import LLMProvider
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
    return OpenAIProvider(settings)


def get_checkpointer(
    request: Request,
) -> BaseCheckpointSaver:
    return request.app.state.checkpointer
