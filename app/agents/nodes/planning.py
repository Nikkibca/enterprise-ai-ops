from typing import Any

from app.agents.state import AgentState, AgentStatus
from app.agents.tool_validation import (
    ToolValidationError,
    validate_tool_call,
)
from app.audit.service import record_audit_event
from app.llm.base import LLMProvider
from app.policy.engine import (
    PolicyDecision,
    evaluate_tool,
)
from app.tools.factory import create_tool_registry
from app.tools.registry import ToolExecutionError


def planning_node(
    state: AgentState,
    *,
    llm_provider: LLMProvider,
    db: Any = None,
) -> AgentState:
    request = state["request"]
    user_id = state["user_id"]
    task_id = state.get("task_id")

    if db is not None and task_id is None:
        raise ValueError(
            "task_id is required when a database session is provided."
        )

    if db is not None:
        record_audit_event(
            db=db,
            task_id=task_id,
            event_type="agent.started",
            actor=user_id,
            details={
                "stage": "planning",
            },
        )

    # The registry is the single source of truth for available tools.
    tool_registry = create_tool_registry()

    try:
        # Give the provider the same catalog that will later be used
        # for deterministic validation.
        plan = llm_provider.create_plan(
            request,
            tool_registry,
        )

        # Never trust the LLM's tool name or arguments.
        validated_tool_call = validate_tool_call(
            plan.tool_call,
            tool_registry,
        )

        # Policy remains deterministic and outside the LLM.
        policy_result = evaluate_tool(
            tool_name=validated_tool_call.tool,
            user_id=user_id,
        )

    except (ToolValidationError, ToolExecutionError) as exc:
        if db is not None:
            record_audit_event(
                db=db,
                task_id=task_id,
                event_type="policy.checked",
                actor=user_id,
                details={
                    "decision": PolicyDecision.DENY,
                    "reason": str(exc),
                },
            )

        return {
            **state,
            "status": AgentStatus.FAILED,
            "error": str(exc),
        }

    approval_required = (
        policy_result.decision
        == PolicyDecision.APPROVAL_REQUIRED
    )

    # Preserve the planning-step contract used by the existing
    # workflow/tests while keeping the actual decision structured.
    planning_steps = [
        *state.get("planning_steps", []),
        f"Request: {request}",
        f"Selected tool: {validated_tool_call.tool}",
        plan.reasoning_summary,
    ]

    if db is not None:
        record_audit_event(
            db=db,
            task_id=task_id,
            event_type="agent.tool_selected",
            actor=user_id,
            details={
                "stage": "planning",
                "available_tools": tool_registry.list_tools(),
                "selected_tool": validated_tool_call.tool,
            },
        )

        record_audit_event(
            db=db,
            task_id=task_id,
            event_type="policy.checked",
            actor=user_id,
            details={
                "tool": validated_tool_call.tool,
                "risk_level": policy_result.risk_level.value,
                "decision": policy_result.decision,
                "reason": policy_result.reason,
                "approval_required": approval_required,
                "required_permission": (
                    policy_result.required_permission
                ),
                "role": policy_result.role,
            },
        )

    # Explicit policy denial.
    if policy_result.decision == PolicyDecision.DENY:
        return {
            **state,
            "status": AgentStatus.FAILED,
            "planning_steps": planning_steps,
            "agent_plan": plan,
            "selected_tool": validated_tool_call.tool,
            "tool_arguments": validated_tool_call.arguments,
            "risk_level": policy_result.risk_level.value,
            "approval_required": False,
            "approval_granted": False,
            "error": policy_result.reason,
        }

    # The graph decides the next stage:
    # - high-risk -> approval
    # - otherwise -> tool execution
    return {
        **state,
        "status": AgentStatus.PLANNING,
        "planning_steps": planning_steps,
        "agent_plan": plan,
        "selected_tool": validated_tool_call.tool,
        "tool_arguments": validated_tool_call.arguments,
        "risk_level": policy_result.risk_level.value,
        "approval_required": approval_required,
        "approval_granted": False,
    }