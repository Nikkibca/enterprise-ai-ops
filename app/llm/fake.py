from app.agents.schemas import AgentPlan


class FakeLLMProvider:
    def __init__(self, plan: AgentPlan):
        self.plan = plan

    def create_plan(self, request: str) -> AgentPlan:
        return self.plan