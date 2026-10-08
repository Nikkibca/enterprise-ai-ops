from typing import Protocol

from app.agents.schemas import AgentPlan
from app.tools.registry import ToolRegistry


class LLMProvider(Protocol):
    def create_plan(
        self,
        request: str,
        tool_registry: ToolRegistry,
    ) -> AgentPlan:
        ...