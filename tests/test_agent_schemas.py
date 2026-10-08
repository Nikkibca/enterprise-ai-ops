import pytest
from pydantic import ValidationError

from app.agents.schemas import (
    AgentPlan,
    InvestigationResult,
)


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


def test_investigation_result_accepts_structured_result():
    result = InvestigationResult(
        summary="Payment failures increased significantly.",
        findings=[
            "Failure count increased by 25%.",
            "The payment worker reported timeout errors.",
        ],
        evidence=[
            {
                "tool": "sql.read",
                "row_count": 1,
                "rows": [
                    {
                        "failure_count": 125,
                    }
                ],
            },
            {
                "tool": "knowledge.search",
                "results": [
                    {
                        "content": "Payment timeout troubleshooting.",
                    }
                ],
            },
        ],
        recommendation="Investigate payment worker timeout configuration.",
        proposed_action="service.restart",
        risk_level="high",
        approval_required=True,
    )

    assert result.summary == (
        "Payment failures increased significantly."
    )
    assert len(result.findings) == 2
    assert len(result.evidence) == 2
    assert result.recommendation is not None
    assert result.proposed_action == "service.restart"
    assert result.risk_level == "high"
    assert result.approval_required is True


def test_investigation_result_defaults_optional_fields():
    result = InvestigationResult(
        summary="Investigation completed.",
    )

    assert result.findings == []
    assert result.evidence == []
    assert result.recommendation is None
    assert result.proposed_action is None
    assert result.risk_level is None
    assert result.approval_required is False


def test_investigation_result_requires_summary():
    with pytest.raises(ValidationError):
        InvestigationResult()