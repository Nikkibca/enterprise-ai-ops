from sqlalchemy.orm import Session

from app.agents.state import AgentState, AgentStatus
from app.models import Task
from app.workflow_status import (
    can_sync_task_status,
    sync_task_status,
)


def verification_node(
    state: AgentState,
    db: Session | None = None,
) -> AgentState:
    tool_result = state.get("tool_result")

    if not tool_result:
        _sync_status(
            db=db,
            state=state,
            status=AgentStatus.FAILED,
        )

        return {
            "status": AgentStatus.FAILED,
            "error": (
                "No tool result available for verification"
            ),
        }

    if tool_result.get("status") not in {
        "success",
        "simulated",
    }:
        _sync_status(
            db=db,
            state=state,
            status=AgentStatus.FAILED,
        )

        return {
            "status": AgentStatus.FAILED,
            "error": (
                "Tool execution did not succeed"
            ),
        }

    _sync_status(
        db=db,
        state=state,
        status=AgentStatus.VERIFYING,
    )

    return {
        "status": AgentStatus.VERIFYING,
        "verification_result": {
            "verified": True,
            "tool": tool_result.get("tool"),
            "status": tool_result.get("status"),
        },
    }


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