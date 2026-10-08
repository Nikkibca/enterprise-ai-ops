
import pytest

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
        "investigation_step": 0,
        "max_investigation_steps": 3,
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

    assert result["investigation_step"] == 3

    assert result["investigation_result"].summary == (
        "Investigation completed successfully using sql.read."
    )

    assert len(
        result["investigation_result"].evidence
    ) == 3

    assert result["investigation_result"].evidence == (
        result["tool_results"]
    )

    assert all(
        evidence["tool"] == "sql.read"
        for evidence in result["investigation_result"].evidence
    )


def test_agent_graph_handles_failed_tool_execution():
    plan = AgentPlan(
        reasoning_summary="Use an unavailable tool.",
        tool_call={
            "tool": "shell.execute",
            "arguments": {},
        },
    )

    provider = FakeLLMProvider(plan)
    graph = build_agent_graph(provider)

    state = {
        "task_id": 1,
        "user_id": "user-123",
        "request": "Run a shell command",
        "status": AgentStatus.IDLE,
        "investigation_step": 0,
        "max_investigation_steps": 3,
    }

    config = {
        "configurable": {
            "thread_id": "test-failed-tool-task",
        }
    }

    result = graph.invoke(
        state,
        config,
    )

    assert result["status"] == AgentStatus.FAILED
    assert result["error"]

