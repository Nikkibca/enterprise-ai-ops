from sqlalchemy.orm import Session

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.agents.nodes.approved_execution import approved_execution_node
from app.agents.nodes.completion import completion_node
from app.agents.nodes.planning import planning_node
from app.agents.nodes.tool_execution import tool_execution_node
from app.agents.nodes.verification import verification_node
from app.agents.state import AgentState, AgentStatus
from app.llm.base import LLMProvider


def route_after_tool_execution(state: AgentState) -> str:
    status = state.get("status")

    if status == AgentStatus.FAILED:
        return "failed"

    if status == AgentStatus.AWAITING_APPROVAL:
        return "awaiting_approval"

    return "verification"


def route_after_approval_interrupt(state: AgentState) -> str:
    if state.get("status") == AgentStatus.FAILED:
        return "failed"

    if state.get("approval_granted") is True:
        return "approved_execution"

    return "failed"


def route_after_approved_execution(state: AgentState) -> str:
    if state.get("status") == AgentStatus.FAILED:
        return "failed"

    return "verification"


def route_after_verification(state: AgentState) -> str:
    if state.get("status") == AgentStatus.FAILED:
        return "failed"

    return "completion"


def approval_interrupt_node(state: AgentState) -> AgentState:
    approval_id = state.get("approval_id")

    if approval_id is None:
        return {
            "status": AgentStatus.FAILED,
            "error": "Cannot pause for approval without approval_id.",
        }

    decision = interrupt(
        {
            "type": "approval",
            "approval_id": approval_id,
            "task_id": state.get("task_id"),
            "tool": state.get("selected_tool"),
            "risk_level": state.get("risk_level"),
            "message": (
                "Human approval is required before this operation "
                "can execute."
            ),
        }
    )

    if decision is True:
        return {
            "status": AgentStatus.AWAITING_APPROVAL,
            "approval_granted": True,
        }

    return {
        "status": AgentStatus.FAILED,
        "approval_granted": False,
        "error": "Approval was rejected.",
    }


def build_agent_graph(
    llm_provider: LLMProvider,
    db: Session | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
):
    graph = StateGraph(AgentState)

    graph.add_node(
        "planning",
        lambda state: planning_node(
            state,
            llm_provider=llm_provider,
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
        "approval_interrupt",
        approval_interrupt_node,
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
        verification_node,
    )

    graph.add_node(
        "completion",
        completion_node,
    )

    graph.add_edge(START, "planning")
    graph.add_edge("planning", "tool_execution")

    graph.add_conditional_edges(
        "tool_execution",
        route_after_tool_execution,
        {
            "verification": "verification",
            "awaiting_approval": "approval_interrupt",
            "failed": END,
        },
    )

    graph.add_conditional_edges(
        "approval_interrupt",
        route_after_approval_interrupt,
        {
            "approved_execution": "approved_execution",
            "failed": END,
        },
    )

    graph.add_conditional_edges(
        "approved_execution",
        route_after_approved_execution,
        {
            "verification": "verification",
            "failed": END,
        },
    )

    graph.add_conditional_edges(
        "verification",
        route_after_verification,
        {
            "completion": "completion",
            "failed": END,
        },
    )

    graph.add_edge("completion", END)

    if checkpointer is None:
        checkpointer = MemorySaver()

    return graph.compile(
        checkpointer=checkpointer,
    )
