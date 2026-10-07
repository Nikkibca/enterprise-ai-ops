from app.agents.graph import build_agent_graph
from app.agents.schemas import AgentPlan
from app.agents.state import AgentStatus
from app.llm.fake import FakeLLMProvider


def test_agent_graph_completes_successfully():
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
    graph = build_agent_graph(provider)

    state = {
        "task_id": 1,
        "user_id": "user-123",
        "request": "Investigate payment failures",
        "status": AgentStatus.IDLE,
    }

    config = {
        "configurable": {
            "thread_id": "test-sql-task",
        }
    }

    result = graph.invoke(
        state,
        config,
    )

    assert result["status"] == AgentStatus.COMPLETED
    assert result["verification_result"]["verified"] is True
    assert result["tool_result"]["tool"] == "sql.read"


def test_agent_graph_stops_on_disallowed_tool():
    plan = AgentPlan(
        reasoning_summary="Attempt an unauthorized operation.",
        tool_call={
            "tool": "shell.execute",
            "arguments": {
                "command": "dir",
            },
        },
    )

    provider = FakeLLMProvider(plan)
    graph = build_agent_graph(provider)

    state = {
        "task_id": 2,
        "user_id": "test-user",
        "request": "Run an unauthorized command",
        "status": AgentStatus.IDLE,
    }

    config = {
        "configurable": {
            "thread_id": "test-disallowed-task",
        }
    }

    result = graph.invoke(
        state,
        config,
    )

    assert result["status"] == AgentStatus.FAILED
    assert "Tool not allowed" in result["error"]

