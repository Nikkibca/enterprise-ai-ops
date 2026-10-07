from typing import Any

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    tool: str = Field(
        description="Name of the tool the model wants to invoke."
    )
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments to pass to the selected tool."
    )


class AgentPlan(BaseModel):
    reasoning_summary: str = Field(
        description="Brief explanation of why the selected tool is appropriate."
    )
    tool_call: ToolCall