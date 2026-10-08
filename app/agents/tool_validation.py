from app.agents.schemas import ToolCall
from app.tools.registry import (
    ToolExecutionError,
    ToolRegistry,
)


class ToolValidationError(Exception):
    pass


def validate_tool_call(
    tool_call: ToolCall,
    registry: ToolRegistry,
) -> ToolCall:
    if not registry.is_registered(tool_call.tool):
        raise ToolValidationError(
            f"Tool not allowed: {tool_call.tool}"
        )

    try:
        validated_arguments = registry.validate_arguments(
            tool_call.tool,
            tool_call.arguments,
        )
    except ToolExecutionError as exc:
        raise ToolValidationError(
            str(exc)
        ) from exc

    return ToolCall(
        tool=tool_call.tool,
        arguments=validated_arguments,
    )