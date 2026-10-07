import pytest
from pydantic import ValidationError

from app.agents.schemas import AgentPlan


def test_agent_plan_accepts_valid_tool_call():
    plan = AgentPlan(
        reasoning_summary="Read payment failure data from the database.",
        tool_call={
            "tool": "sql.read",
            "arguments": {
                "query": "SELECT COUNT(*) FROM payment_failures",
            },
        },
    )

    assert plan.tool_call.tool == "sql.read"
    assert plan.tool_call.arguments["query"].startswith("SELECT")


def test_agent_plan_defaults_to_empty_arguments():
    plan = AgentPlan(
        reasoning_summary="Search the enterprise knowledge base.",
        tool_call={
            "tool": "knowledge.search",
        },
    )

    assert plan.tool_call.arguments == {}


def test_agent_plan_requires_tool_call():
    with pytest.raises(ValidationError):
        AgentPlan(
            reasoning_summary="Investigate the issue.",
        )
