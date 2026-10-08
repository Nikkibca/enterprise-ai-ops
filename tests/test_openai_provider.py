from app.agents.schemas import AgentPlan
from app.llm.openai_provider import (
    OpenAIPlanResponse,
    OpenAIProvider,
    convert_openai_plan,
)


class FakeResponses:
    def __init__(self, parsed_response):
        self.parsed_response = parsed_response
        self.last_kwargs = None

    def parse(self, **kwargs):
        self.last_kwargs = kwargs

        return type(
            "FakeResponse",
            (),
            {
                "output_parsed": self.parsed_response,
            },
        )()


class FakeOpenAIClient:
    def __init__(self, parsed_response):
        self.responses = FakeResponses(parsed_response)


def build_provider(
    parsed_response: OpenAIPlanResponse,
) -> OpenAIProvider:
    provider = OpenAIProvider.__new__(OpenAIProvider)

    provider.settings = type(
        "FakeSettings",
        (),
        {
            "openai_api_key": "test-key",
            "openai_model": "gpt-6-luna",
        },
    )()

    provider.client = FakeOpenAIClient(
        parsed_response,
    )

    return provider


def test_convert_openai_plan_sql():
    response = OpenAIPlanResponse(
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

    result = convert_openai_plan(response)

    assert isinstance(result, AgentPlan)
    assert result.reasoning_summary == (
        "Use SQL to investigate payment failures."
    )
    assert result.tool_call.tool == "sql.read"
    assert result.tool_call.arguments == {
        "query": (
            "SELECT COUNT(*) "
            "FROM payment_failures"
        ),
    }


def test_convert_openai_plan_knowledge():
    response = OpenAIPlanResponse(
        reasoning_summary=(
            "Use enterprise knowledge to troubleshoot "
            "the payment timeout."
        ),
        tool_call={
            "tool": "knowledge.search",
            "arguments": {
                "query": "payment timeout troubleshooting",
            },
        },
    )

    result = convert_openai_plan(response)

    assert result.tool_call.tool == "knowledge.search"
    assert result.tool_call.arguments == {
        "query": "payment timeout troubleshooting",
    }


def test_convert_openai_plan_python_analysis():
    response = OpenAIPlanResponse(
        reasoning_summary=(
            "Use numerical analysis to summarize "
            "the supplied failure counts."
        ),
        tool_call={
            "tool": "python.analysis",
            "arguments": {
                "operation": "summary",
                "values": [10, 20, 30],
            },
        },
    )

    result = convert_openai_plan(response)

    assert result.tool_call.tool == "python.analysis"
    assert result.tool_call.arguments == {
        "operation": "summary",
        "values": [10, 20, 30],
    }


def test_convert_openai_plan_service_restart():
    response = OpenAIPlanResponse(
        reasoning_summary=(
            "Restart the payment worker to recover "
            "the unhealthy service."
        ),
        tool_call={
            "tool": "service.restart",
            "arguments": {
                "service": "payment-worker",
            },
        },
    )

    result = convert_openai_plan(response)

    assert result.tool_call.tool == "service.restart"
    assert result.tool_call.arguments == {
        "service": "payment-worker",
    }


def test_openai_provider_returns_sql_plan():
    parsed_response = OpenAIPlanResponse(
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

    provider = build_provider(parsed_response)

    result = provider.create_plan(
        "Why did payment failures increase yesterday?"
    )

    assert isinstance(result, AgentPlan)
    assert result.tool_call.tool == "sql.read"
    assert result.tool_call.arguments["query"].startswith(
        "SELECT"
    )


def test_openai_provider_returns_knowledge_plan():
    parsed_response = OpenAIPlanResponse(
        reasoning_summary=(
            "Use enterprise knowledge to troubleshoot "
            "payment timeouts."
        ),
        tool_call={
            "tool": "knowledge.search",
            "arguments": {
                "query": "payment timeout troubleshooting",
            },
        },
    )

    provider = build_provider(parsed_response)

    result = provider.create_plan(
        "How do we troubleshoot payment timeout errors?"
    )

    assert isinstance(result, AgentPlan)
    assert result.tool_call.tool == "knowledge.search"
    assert result.tool_call.arguments["query"] == (
        "payment timeout troubleshooting"
    )


def test_openai_provider_returns_python_analysis_plan():
    parsed_response = OpenAIPlanResponse(
        reasoning_summary=(
            "Use numerical analytics to summarize "
            "the supplied values."
        ),
        tool_call={
            "tool": "python.analysis",
            "arguments": {
                "operation": "summary",
                "values": [10, 20, 30],
            },
        },
    )

    provider = build_provider(parsed_response)

    result = provider.create_plan(
        "Summarize these payment failure counts: "
        "10, 20, 30."
    )

    assert isinstance(result, AgentPlan)
    assert result.tool_call.tool == "python.analysis"
    assert result.tool_call.arguments == {
        "operation": "summary",
        "values": [10, 20, 30],
    }


def test_openai_provider_returns_service_restart_plan():
    parsed_response = OpenAIPlanResponse(
        reasoning_summary=(
            "Restart the payment worker."
        ),
        tool_call={
            "tool": "service.restart",
            "arguments": {
                "service": "payment-worker",
            },
        },
    )

    provider = build_provider(parsed_response)

    result = provider.create_plan(
        "Restart the payment worker."
    )

    assert isinstance(result, AgentPlan)
    assert result.tool_call.tool == "service.restart"
    assert result.tool_call.arguments == {
        "service": "payment-worker",
    }


def test_openai_provider_uses_configured_model():
    parsed_response = OpenAIPlanResponse(
        reasoning_summary="Use SQL.",
        tool_call={
            "tool": "sql.read",
            "arguments": {
                "query": "SELECT 1",
            },
        },
    )

    provider = build_provider(parsed_response)

    provider.create_plan("Check the database.")

    kwargs = provider.client.responses.last_kwargs

    assert kwargs["model"] == "gpt-6-luna"


def test_openai_provider_uses_structured_output():
    parsed_response = OpenAIPlanResponse(
        reasoning_summary="Use SQL.",
        tool_call={
            "tool": "sql.read",
            "arguments": {
                "query": "SELECT 1",
            },
        },
    )

    provider = build_provider(parsed_response)

    provider.create_plan("Check the database.")

    kwargs = provider.client.responses.last_kwargs

    assert kwargs["text_format"] is OpenAIPlanResponse


def test_openai_provider_rejects_missing_structured_output():
    class EmptyResponses:
        def parse(self, **kwargs):
            return type(
                "FakeResponse",
                (),
                {
                    "output_parsed": None,
                },
            )()

    provider = OpenAIProvider.__new__(OpenAIProvider)

    provider.settings = type(
        "FakeSettings",
        (),
        {
            "openai_api_key": "test-key",
            "openai_model": "gpt-6-luna",
        },
    )()

    provider.client = type(
        "FakeClient",
        (),
        {
            "responses": EmptyResponses(),
        },
    )()

    try:
        provider.create_plan(
            "Check payment failures."
        )
        assert False, (
            "Expected ValueError when structured "
            "output is missing."
        )
    except ValueError as exc:
        assert str(exc) == (
            "OpenAI returned no structured plan."
        )

def test_openai_provider_uses_tool_registry_catalog():
    parsed_response = OpenAIPlanResponse(
        reasoning_summary="Use the custom tool.",
        tool_call={
            "tool": "custom.test",
            "arguments": {
                "query": "test",
            },
        },
    )

    provider = build_provider(parsed_response)

    class FakeToolRegistry:
        def build_llm_catalog(self):
            return [
                {
                    "name": "custom.test",
                    "description": "A custom test tool.",
                    "risk_level": "low",
                    "required_permission": "test.execute",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                            },
                        },
                        "required": ["query"],
                    },
                }
            ]

    registry = FakeToolRegistry()

    result = provider.create_plan(
        "Run the custom test tool.",
        tool_registry=registry,
    )

    assert result.tool_call.tool == "custom.test"

    kwargs = provider.client.responses.last_kwargs

    instructions = kwargs["instructions"]

    assert "custom.test" in instructions
    assert "A custom test tool." in instructions
    assert "test.execute" in instructions
    assert "Run the custom test tool." not in instructions


def test_openai_provider_default_registry_contains_registered_tools():
    parsed_response = OpenAIPlanResponse(
        reasoning_summary="Use SQL.",
        tool_call={
            "tool": "sql.read",
            "arguments": {
                "query": "SELECT 1",
            },
        },
    )

    provider = build_provider(parsed_response)

    provider.create_plan("Check the database.")

    kwargs = provider.client.responses.last_kwargs
    instructions = kwargs["instructions"]

    assert "knowledge.search" in instructions
    assert "sql.read" in instructions
    assert "python.analysis" in instructions
    assert "service.restart" in instructions

    assert "knowledge.read" in instructions
    assert "data.read" in instructions
    assert "analytics.execute" in instructions
    assert "operations.restart" in instructions    