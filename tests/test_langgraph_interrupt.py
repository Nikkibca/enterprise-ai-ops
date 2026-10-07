from typing_extensions import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class InterruptState(TypedDict, total=False):
    message: str
    approved: bool
    result: str


def approval_node(state: InterruptState) -> InterruptState:
    decision = interrupt(
        {
            "type": "approval",
            "message": "Approve this operation?",
        }
    )

    return {
        "approved": bool(decision),
    }


def execution_node(state: InterruptState) -> InterruptState:
    if not state.get("approved"):
        return {
            "result": "rejected",
        }

    return {
        "result": "executed",
    }


def build_test_graph():
    graph = StateGraph(InterruptState)

    graph.add_node(
        "approval",
        approval_node,
    )

    graph.add_node(
        "execution",
        execution_node,
    )

    graph.add_edge(
        START,
        "approval",
    )

    graph.add_edge(
        "approval",
        "execution",
    )

    graph.add_edge(
        "execution",
        END,
    )

    checkpointer = MemorySaver()

    return graph.compile(
        checkpointer=checkpointer,
    )


def test_graph_pauses_for_approval():
    graph = build_test_graph()

    config = {
        "configurable": {
            "thread_id": "test-thread-1",
        }
    }

    result = graph.invoke(
        {
            "message": "Restart payment worker",
        },
        config,
    )

    assert "__interrupt__" in result

    interrupt_value = result["__interrupt__"][0].value

    assert interrupt_value["type"] == "approval"
    assert interrupt_value["message"] == "Approve this operation?"


def test_graph_resumes_after_approval():
    graph = build_test_graph()

    config = {
        "configurable": {
            "thread_id": "test-thread-2",
        }
    }

    first_result = graph.invoke(
        {
            "message": "Restart payment worker",
        },
        config,
    )

    assert "__interrupt__" in first_result

    second_result = graph.invoke(
        Command(resume=True),
        config,
    )

    assert second_result["approved"] is True
    assert second_result["result"] == "executed"

