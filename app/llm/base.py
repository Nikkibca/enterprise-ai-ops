from typing import Protocol

from app.agents.schemas import AgentPlan


class LLMProvider(Protocol):
    def create_plan(
        self,
        request: str,
    ) -> AgentPlan:
        ...