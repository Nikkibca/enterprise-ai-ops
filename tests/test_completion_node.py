from app.agents.nodes.completion import completion_node
from app.agents.state import AgentStatus


def test_completion_succeeds_after_verification():
    state = {
        "verification_result": {
            "verified": True,
            "tool": "sql.read",
        },
    }

    result = completion_node(state)

    assert result["status"] == AgentStatus.COMPLETED
    assert result["final_response"] == "Task completed successfully."


def test_completion_fails_without_verification():
    state = {}

    result = completion_node(state)

    assert result["status"] == AgentStatus.FAILED
    assert result["error"] == "Cannot complete without verification"


def test_completion_fails_when_verification_failed():
    state = {
        "verification_result": {
            "verified": False,
            "tool": "sql.read",
        },
    }

    result = completion_node(state)

    assert result["status"] == AgentStatus.FAILED
    assert result["error"] == "Verification did not succeed"
