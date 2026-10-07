from enum import Enum
from typing import Any, TypedDict

from app.agents.schemas import AgentPlan


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
    agent_plan: AgentPlan

    selected_tool: str
    tool_arguments: dict[str, Any]
    tool_result: Any

    risk_level: str
    approval_required: bool
    approval_granted: bool
    approval_id: int

    verification_result: Any

    final_response: str
    error: str