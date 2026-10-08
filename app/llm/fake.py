from app.agents.schemas import AgentPlan
from app.tools.registry import ToolRegistry


class FakeLLMProvider:
    def __init__(self, plan: AgentPlan):
        self.plan = plan

    def create_plan(
        self,
        request: str,
        tool_registry: ToolRegistry | None = None,
    ) -> AgentPlan:
        return self.plan