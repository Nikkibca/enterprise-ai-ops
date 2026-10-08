from sqlalchemy.orm import Session

from app.agents.schemas import InvestigationResult
from app.agents.state import AgentState, AgentStatus
from app.models import Task
from app.workflow_status import (
    can_sync_task_status,
    sync_task_status,
)


def completion_node(
    state: AgentState,
    db: Session | None = None,
) -> AgentState:
    verification_result = state.get("verification_result")

    if not verification_result:
        _sync_status(
            db=db,
            state=state,
            status=AgentStatus.FAILED,
        )
        return {
            "status": AgentStatus.FAILED,
            "error": "Cannot complete without verification",
        }

    if not verification_result.get("verified"):
        _sync_status(
            db=db,
            state=state,
            status=AgentStatus.FAILED,
        )
        return {
            "status": AgentStatus.FAILED,
            "error": "Verification did not succeed",
        }

    investigation_result = _build_investigation_result(
        state=state,
    )

    _sync_status(
        db=db,
        state=state,
        status=AgentStatus.COMPLETED,
    )

    return {
        "status": AgentStatus.COMPLETED,
        "investigation_result": investigation_result,
        "final_response": investigation_result.summary,
    }


def _build_investigation_result(
    state: AgentState,
) -> InvestigationResult:
    tool_name = state.get(
        "selected_tool",
        state.get(
            "verification_result",
            {},
        ).get(
            "tool",
            "unknown",
        ),
    )

    # Prefer the accumulated tool history.
    #
    # This allows future multi-step investigations to preserve
    # evidence from every tool execution.
    tool_results = list(
        state.get("tool_results", [])
    )

    # Backward compatibility:
    # If an older workflow only provides tool_result,
    # use it as the evidence source.
    if not tool_results:
        tool_result = state.get("tool_result")

        if tool_result:
            tool_results = [
                tool_result,
            ]

    findings: list[str] = []

    for result in tool_results:
        result_tool = result.get(
            "tool",
            "unknown",
        )

        status = result.get("status")

        if status:
            findings.append(
                f"Tool '{result_tool}' completed "
                f"with status '{status}'."
            )

        if "row_count" in result:
            findings.append(
                f"Tool returned {result['row_count']} rows."
            )

        if "service" in result:
            findings.append(
                f"Operational service: "
                f"{result['service']}."
            )

    summary = (
        f"Investigation completed successfully "
        f"using {tool_name}."
    )

    return InvestigationResult(
        summary=summary,
        findings=findings,
        evidence=tool_results,
        recommendation=None,
        proposed_action=(
            tool_name
            if tool_name == "service.restart"
            else None
        ),
        risk_level=state.get("risk_level"),
        approval_required=state.get(
            "approval_required",
            False,
        ),
    )


def _sync_status(
    db: Session | None,
    state: AgentState,
    status: AgentStatus,
) -> None:
    if db is None or state.get("task_id") is None:
        return

    task = db.get(
        Task,
        state["task_id"],
    )

    if task is None:
        return

    if not can_sync_task_status(
        task=task,
        agent_status=status,
    ):
        return

    sync_task_status(
        db=db,
        task=task,
        agent_status=status,
    )

