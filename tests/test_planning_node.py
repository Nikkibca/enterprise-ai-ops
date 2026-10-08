from app.agents.nodes.planning import planning_node
from app.agents.schemas import AgentPlan
from app.agents.state import AgentStatus
from app.llm.fake import FakeLLMProvider


def test_planning_node_uses_llm_provider():
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

    state = {
        "task_id": 1,
        "user_id": "user-123",
        "request": "Investigate payment failures",
        "status": AgentStatus.IDLE,
    }

    result = planning_node(
        state,
        llm_provider=provider,
    )

    assert result["status"] == AgentStatus.PLANNING

    assert len(result["planning_steps"]) == 3
    assert "Investigate payment failures" in result["planning_steps"][0]

    assert result["agent_plan"] == plan
    assert result["agent_plan"].tool_call.tool == "sql.read"

    assert result["selected_tool"] == "sql.read"
    assert result["tool_arguments"] == {
        "query": "SELECT COUNT(*) FROM payment_failures",
    }
