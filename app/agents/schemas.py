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
        description=(
            "Brief explanation of why the selected tool "
            "is appropriate."
        )
    )
    tool_call: ToolCall


class InvestigationResult(BaseModel):
    summary: str = Field(
        description="Concise summary of the investigation outcome."
    )
    findings: list[str] = Field(
        default_factory=list,
        description="Key findings supported by the investigation."
    )
    evidence: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Structured evidence produced by tools."
    )
    recommendation: str | None = Field(
        default=None,
        description="Recommended next step, if applicable."
    )
    proposed_action: str | None = Field(
        default=None,
        description="Operational action proposed by the workflow."
    )
    risk_level: str | None = Field(
        default=None,
        description="Risk level associated with the proposed action."
    )
    approval_required: bool = Field(
        default=False,
        description="Whether human approval is required."
    )