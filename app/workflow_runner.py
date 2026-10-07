from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.types import Command
from sqlalchemy.orm import Session

from app.agents.graph import build_agent_graph
from app.agents.state import AgentState
from app.llm.base import LLMProvider


class WorkflowRunner:
    def __init__(
        self,
        llm_provider: LLMProvider,
        db: Session | None = None,
        checkpointer: BaseCheckpointSaver | None = None,
    ):
        self.llm_provider = llm_provider
        self.db = db
        self.checkpointer = checkpointer

        self.graph = build_agent_graph(
            llm_provider,
            db=db,
            checkpointer=checkpointer,
        )

    def start(
        self,
        state: AgentState,
        *,
        thread_id: str,
    ) -> AgentState:
        config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }

        return self.graph.invoke(
            state,
            config,
        )

    def resume(
        self,
        *,
        thread_id: str,
        approved: bool = True,
    ) -> AgentState:
        config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }

        return self.graph.invoke(
            Command(resume=approved),
            config,
        )
