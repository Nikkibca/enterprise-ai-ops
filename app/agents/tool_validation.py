from app.agents.schemas import ToolCall
from app.tools.registry import ToolRegistry


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

    return tool_call