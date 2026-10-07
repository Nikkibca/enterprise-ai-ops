import pytest

from app.agents.schemas import ToolCall
from app.agents.tool_validation import (
    ToolValidationError,
    validate_tool_call,
)
from app.tools.factory import create_tool_registry


@pytest.fixture
def registry():
    return create_tool_registry()


def test_knowledge_search_is_allowed(registry):
    tool_call = ToolCall(
        tool="knowledge.search",
        arguments={"query": "payment timeout troubleshooting"},
    )

    result = validate_tool_call(
        tool_call,
        registry,
    )

    assert result.tool == "knowledge.search"


def test_sql_read_is_allowed(registry):
    tool_call = ToolCall(
        tool="sql.read",
        arguments={"query": "SELECT COUNT(*) FROM payments"},
    )

    result = validate_tool_call(
        tool_call,
        registry,
    )

    assert result.tool == "sql.read"


def test_shell_execute_is_rejected(registry):
    tool_call = ToolCall(
        tool="shell.execute",
        arguments={"command": "dir"},
    )

    with pytest.raises(
        ToolValidationError,
        match="Tool not allowed: shell.execute",
    ):
        validate_tool_call(
            tool_call,
            registry,
        )


def test_unknown_tool_is_rejected(registry):
    tool_call = ToolCall(
        tool="unknown.tool",
        arguments={},
    )

    with pytest.raises(
        ToolValidationError,
        match="Tool not allowed: unknown.tool",
    ):
        validate_tool_call(
            tool_call,
            registry,
        )