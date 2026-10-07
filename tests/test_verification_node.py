from app.agents.nodes.verification import verification_node
from app.agents.state import AgentStatus


def test_verification_succeeds_for_successful_tool_result():
    state = {
        "tool_result": {
            "tool": "sql.read",
            "status": "simulated",
            "message": "Tool execution placeholder",
        },
    }

    result = verification_node(state)

    assert result["status"] == AgentStatus.VERIFYING
    assert result["verification_result"]["verified"] is True
    assert result["verification_result"]["tool"] == "sql.read"


def test_verification_fails_without_tool_result():
    state = {}

    result = verification_node(state)

    assert result["status"] == AgentStatus.FAILED
    assert result["error"] == "No tool result available for verification"


def test_verification_fails_for_unsuccessful_tool_result():
    state = {
        "tool_result": {
            "tool": "sql.read",
            "status": "failed",
        },
    }

    result = verification_node(state)

    assert result["status"] == AgentStatus.FAILED
    assert result["error"] == "Tool execution did not succeed"
