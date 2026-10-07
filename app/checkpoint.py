from contextlib import contextmanager
from typing import Iterator

from langgraph.checkpoint.postgres import PostgresSaver

from app.llm.settings import LLMSettings


@contextmanager
def get_checkpointer() -> Iterator[PostgresSaver]:
    settings = LLMSettings()

    with PostgresSaver.from_conn_string(
        settings.langgraph_checkpoint_database_url,
    ) as checkpointer:
        checkpointer.setup()
        yield checkpointer
