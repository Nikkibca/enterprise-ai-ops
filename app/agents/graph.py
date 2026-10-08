from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from sqlalchemy.orm import Session

from app.agents.nodes.approved_execution import approved_execution_node
from app.agents.nodes.completion import completion_node
from app.agents.nodes.planning import planning_node
from app.agents.nodes.tool_execution import tool_execution_node
from app.agents.nodes.verification import verification_node
from app.agents.state import AgentState, AgentStatus
from app.llm.base import LLMProvider


def build_agent_graph(
    llm_provider: LLMProvider,
    db: Session | None = None,
    checkpointer: Any | None = None,
):
    graph = StateGraph(AgentState)

    graph.add_node(
        "planning",
        lambda state: planning_node(
            state,
            llm_provider=llm_provider,
            db=db,
        ),
    )

    graph.add_node(
        "tool_execution",
        lambda state: tool_execution_node(
            state,
            db=db,
        ),
    )

    graph.add_node(
        "approved_execution",
        lambda state: approved_execution_node(
            state,
            db=db,
        ),
    )

    graph.add_node(
        "verification",
        lambda state: verification_node(
            state,
            db=db,
        ),
    )

    graph.add_node(
        "completion",
        lambda state: completion_node(
            state,
            db=db,
        ),
    )

    graph.add_edge(
        START,
        "planning",
    )

    graph.add_edge(
        "planning",
        "tool_execution",
    )

    def route_after_tool_execution(state: AgentState):
        status = state.get("status")

        if status == AgentStatus.FAILED:
            return END

        if status == AgentStatus.AWAITING_APPROVAL:
            return "approval_interrupt"

        return "verification"

    graph.add_conditional_edges(
        "tool_execution",
        route_after_tool_execution,
        {
            END: END,
            "approval_interrupt": "approval_interrupt",
            "verification": "verification",
        },
    )

    def approval_interrupt_node(state: AgentState):
        approval_id = state.get("approval_id")

        decision = interrupt(
            {
                "type": "approval",
                "approval_id": approval_id,
                "task_id": state.get("task_id"),
                "tool": state.get("selected_tool"),
                "risk_level": state.get("risk_level"),
            }
        )

        # Backward-compatible support for direct LangGraph resume(True)
        # while the API uses the stronger structured decision.
        if isinstance(decision, dict):
            approved = decision.get("approved") is True
            decided_by = decision.get("decided_by")
        else:
            approved = decision is True
            decided_by = None

        if approved:
            result = {
                "approval_granted": True,
                "status": AgentStatus.EXECUTING_ACTION,
                "error": "",
            }

            if isinstance(decided_by, str) and decided_by.strip():
                result["approval_decided_by"] = decided_by.strip()

            return result

        return {
            "approval_granted": False,
            "status": AgentStatus.FAILED,
            "error": "Human approval was rejected.",
        }

    graph.add_node(
        "approval_interrupt",
        approval_interrupt_node,
    )

    def route_after_approval(state: AgentState):
        if state.get("approval_granted") is True:
            return "approved_execution"

        return END

    graph.add_conditional_edges(
        "approval_interrupt",
        route_after_approval,
        {
            "approved_execution": "approved_execution",
            END: END,
        },
    )

    def route_after_approved_execution(state: AgentState):
        if state.get("status") == AgentStatus.FAILED:
            return END

        return "verification"

    graph.add_conditional_edges(
        "approved_execution",
        route_after_approved_execution,
        {
            "verification": "verification",
            END: END,
        },
    )

    def route_after_verification(state: AgentState):
        if state.get("status") == AgentStatus.FAILED:
            return END

        if state.get("approval_granted") is True:
            return "completion"

        current_step = state.get("investigation_step", 0)
        max_steps = state.get("max_investigation_steps", 3)

        if current_step < max_steps:
            return "planning"

        return "completion"

    graph.add_conditional_edges(
        "verification",
        route_after_verification,
        {
            "planning": "planning",
            "completion": "completion",
            END: END,
        },
    )

    graph.add_edge(
        "completion",
        END,
    )

    if checkpointer is None:
        checkpointer = MemorySaver()

    return graph.compile(
        checkpointer=checkpointer,
    )