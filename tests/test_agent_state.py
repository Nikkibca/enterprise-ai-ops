from app.agents.state import AgentState, AgentStatus


def test_agent_state_supports_workflow_fields():
    state: AgentState = {
        "task_id": 1,
        "user_id": "test-user",
        "request": "Investigate payment failures",
        "status": AgentStatus.PLANNING,
        "plan": [
            "Search operational knowledge",
            "Analyze payment failure data",
        ],
        "selected_tool": "sql.read",
        "tool_arguments": {
            "query": "SELECT COUNT(*) FROM payment_failures",
        },
        "risk_level": "low",
        "approval_required": False,
        "approval_granted": False,
    }

    assert state["status"] == AgentStatus.PLANNING
    assert state["selected_tool"] == "sql.read"
    assert state["approval_required"] is False
    assert len(state["plan"]) == 2
