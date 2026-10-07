from app.agents.schemas import AgentPlan
from app.llm.openai_provider import (
    OpenAIPlanResponse,
    OpenAIProvider,
    convert_openai_plan,
)


class FakeResponses:
    def parse(self, **kwargs):
        return type(
            "FakeResponse",
            (),
            {
                "output_parsed": OpenAIPlanResponse(
                    reasoning_summary=(
                        "Use SQL to investigate payment failures."
                    ),
                    tool_call={
                        "tool": "sql.read",
                        "arguments": {
                            "query": (
                                "SELECT COUNT(*) "
                                "FROM payment_failures"
                            ),
                        },
                    },
                )
            },
        )()


class FakeOpenAIClient:
    def __init__(self):
        self.responses = FakeResponses()


def test_convert_openai_plan():
    response = OpenAIPlanResponse(
        reasoning_summary=(
            "Use SQL to investigate payment failures."
        ),
        tool_call={
            "tool": "sql.read",
            "arguments": {
                "query": (
                    "SELECT COUNT(*) FROM payment_failures"
                ),
            },
        },
    )

    result = convert_openai_plan(response)

    assert isinstance(result, AgentPlan)
    assert result.tool_call.tool == "sql.read"
    assert result.tool_call.arguments == {
        "query": "SELECT COUNT(*) FROM payment_failures",
    }


def test_openai_provider_returns_agent_plan():
    provider = OpenAIProvider.__new__(OpenAIProvider)

    provider.settings = type(
        "FakeSettings",
        (),
        {
            "openai_api_key": "test-key",
            "openai_model": "gpt-6-luna",
        },
    )()

    provider.client = FakeOpenAIClient()

    result = provider.create_plan(
        "Why did payment failures increase yesterday?"
    )

    assert isinstance(result, AgentPlan)
    assert result.tool_call.tool == "sql.read"
    assert result.tool_call.arguments["query"].startswith(
        "SELECT"
    )