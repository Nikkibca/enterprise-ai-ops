from app.agents.schemas import AgentPlan
from app.llm.fake import FakeLLMProvider


def test_fake_llm_provider_returns_agent_plan():
    plan = AgentPlan(
        reasoning_summary="Investigate payment failures using SQL.",
        tool_call={
            "tool": "sql.read",
            "arguments": {
                "query": "SELECT COUNT(*) FROM payment_failures",
            },
        },
    )

    provider = FakeLLMProvider(plan)

    result = provider.create_plan(
        "Why did payment failures increase yesterday?"
    )

    assert result == plan
    assert result.tool_call.tool == "sql.read"
    assert result.tool_call.arguments["query"].startswith("SELECT")
