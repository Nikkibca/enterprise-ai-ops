
from contextlib import contextmanager
from typing import Iterator

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from app.agents.schemas import AgentPlan, ToolCall
from app.llm.settings import LLMSettings


@contextmanager
def get_checkpointer() -> Iterator[PostgresSaver]:
    settings = LLMSettings()

    serializer = JsonPlusSerializer(
        allowed_msgpack_modules=[
            (AgentPlan.__module__, AgentPlan.__name__),
            (ToolCall.__module__, ToolCall.__name__),
        ],
    )

    with PostgresSaver.from_conn_string(
        settings.langgraph_checkpoint_database_url,
    ) as checkpointer:
        checkpointer.serde = serializer
        checkpointer.setup()
        yield checkpointer
