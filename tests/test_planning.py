from app.agents.nodes.planning import planning_node
from app.agents.schemas import AgentPlan, ToolCall
from app.llm.fake import FakeLLMProvider


def test_planning_node_transfers_structured_agent_plan():
    plan = AgentPlan(
        reasoning_summary=(
            "Use SQL to investigate payment failures."
        ),
        tool_call=ToolCall(
            tool="sql.read",
            arguments={
                "query": (
                    "SELECT COUNT(*) "
                    "FROM payment_failures"
                ),
            },
        ),
    )

    provider = FakeLLMProvider(plan)

    state = {
        "request": (
            "Why did payment failures increase yesterday?"
        ),
        "user_id": "user-123",
    }

    result = planning_node(
        state,
        llm_provider=provider,
    )

    assert result["status"] == "planning"
    assert result["selected_tool"] == "sql.read"
    assert result["tool_arguments"] == {
        "query": (
            "SELECT COUNT(*) "
            "FROM payment_failures"
        ),
    }
    assert result["agent_plan"] == plan


def test_planning_node_supports_knowledge_search():
    plan = AgentPlan(
        reasoning_summary=(
            "Use enterprise knowledge to troubleshoot "
            "the payment timeout."
        ),
        tool_call=ToolCall(
            tool="knowledge.search",
            arguments={
                "query": "payment timeout troubleshooting",
            },
        ),
    )

    provider = FakeLLMProvider(plan)

    state = {
        "request": (
            "How do we troubleshoot payment timeout errors?"
        ),
        "user_id": "user-123",
    }

    result = planning_node(
        state,
        llm_provider=provider,
    )

    assert result["status"] == "planning"
    assert result["selected_tool"] == "knowledge.search"
    assert result["tool_arguments"] == {
        "query": "payment timeout troubleshooting",
        "top_k": 5,
    }


def test_planning_node_supports_python_analysis():
    plan = AgentPlan(
        reasoning_summary=(
            "Use numerical analysis to summarize "
            "the supplied values."
        ),
        tool_call=ToolCall(
            tool="python.analysis",
            arguments={
                "operation": "summary",
                "values": [10, 20, 30],
            },
        ),
    )

    provider = FakeLLMProvider(plan)

    state = {
        "request": (
            "Summarize these payment failure counts."
        ),
        "user_id": "user-123",
    }

    result = planning_node(
        state,
        llm_provider=provider,
    )

    assert result["status"] == "planning"
    assert result["selected_tool"] == "python.analysis"
    assert result["tool_arguments"] == {
        "operation": "summary",
        "values": [10, 20, 30],
    }


def test_planning_node_supports_service_restart():
    plan = AgentPlan(
        reasoning_summary=(
            "The payment worker should be restarted."
        ),
        tool_call=ToolCall(
            tool="service.restart",
            arguments={
                "service": "payment-worker",
            },
        ),
    )

    provider = FakeLLMProvider(plan)

    state = {
        "request": "Restart the payment worker.",
        "user_id": "manager-123",
    }

    result = planning_node(
        state,
        llm_provider=provider,
    )

    assert result["status"] == "planning"
    assert result["selected_tool"] == "service.restart"
    assert result["tool_arguments"] == {
        "service": "payment-worker",
    }
    assert result["approval_required"] is True