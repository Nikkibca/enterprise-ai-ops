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
    assert (
        result["final_response"]
        == "Investigation completed successfully using sql.read."
    )

    investigation_result = result["investigation_result"]

    assert investigation_result.summary == (
        "Investigation completed successfully using sql.read."
    )
    assert investigation_result.findings == []
    assert investigation_result.evidence == []
    assert investigation_result.risk_level is None
    assert investigation_result.approval_required is False


def test_completion_builds_structured_investigation_result():
    state = {
        "request": "Investigate payment failures.",
        "selected_tool": "sql.read",
        "tool_result": {
            "tool": "sql.read",
            "status": "success",
            "query": "SELECT COUNT(*) FROM payment_failures",
            "row_count": 1,
            "rows": [
                {
                    "count": 42,
                },
            ],
        },
        "risk_level": "low",
        "approval_required": False,
        "verification_result": {
            "verified": True,
            "tool": "sql.read",
            "status": "success",
        },
    }

    result = completion_node(state)

    assert result["status"] == AgentStatus.COMPLETED

    investigation_result = result["investigation_result"]

    assert investigation_result.summary == (
        "Investigation completed successfully using sql.read."
    )

    assert investigation_result.findings == [
        "Tool 'sql.read' completed with status 'success'.",
        "Tool returned 1 rows.",
    ]

    assert investigation_result.evidence == [
        {
            "tool": "sql.read",
            "status": "success",
            "query": "SELECT COUNT(*) FROM payment_failures",
            "row_count": 1,
            "rows": [
                {
                    "count": 42,
                },
            ],
        }
    ]

    assert investigation_result.recommendation is None
    assert investigation_result.proposed_action is None
    assert investigation_result.risk_level == "low"
    assert investigation_result.approval_required is False


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