from enum import Enum
from typing import Any, TypedDict

from app.agents.schemas import (
    AgentPlan,
    InvestigationResult,
)


class AgentStatus(str, Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING_TOOL = "executing_tool"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING_ACTION = "executing_action"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentState(TypedDict, total=False):
    task_id: int
    user_id: str
    request: str

    status: AgentStatus

    planning_steps: list[str]
    investigation_step: int
    max_investigation_steps: int

    agent_plan: AgentPlan

    selected_tool: str
    tool_arguments: dict[str, Any]

    tool_result: Any
    tool_results: list[dict[str, Any]]

    risk_level: str
    approval_required: bool
    approval_granted: bool
    approval_id: int
    approval_decided_by: str

    verification_result: Any

    investigation_result: InvestigationResult
    final_response: str

    error: str