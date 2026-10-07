from langgraph.types import Command

from app.agents.graph import build_agent_graph
from app.agents.schemas import AgentPlan, ToolCall
from app.agents.state import AgentStatus
from app.llm.fake import FakeLLMProvider


def test_real_agent_graph_interrupts_for_high_risk_action(db_session):
    from app.models import Task

    task = Task(
        user_id="manager-123",
        request="Restart payment worker",
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    provider = FakeLLMProvider(
        AgentPlan(
            reasoning_summary="Restarting the payment worker requires a controlled operational action.",
            tool_call=ToolCall(
                tool="service.restart",
                arguments={
                    "service": "payment-worker",
                },
            ),
        )
    )

    graph = build_agent_graph(
        provider,
        db=db_session,
    )

    config = {
        "configurable": {
            "thread_id": f"task-{task.id}",
        }
    }

    result = graph.invoke(
        {
            "task_id": task.id,
            "user_id": task.user_id,
            "request": task.request,
        },
        config,
    )

    assert "__interrupt__" in result

    interrupt_value = result["__interrupt__"][0].value

    assert interrupt_value["type"] == "approval"
    assert interrupt_value["approval_id"] is not None
    assert interrupt_value["task_id"] == task.id
    assert interrupt_value["tool"] == "service.restart"
    assert interrupt_value["risk_level"] == "high"

    snapshot = graph.get_state(config)

    assert snapshot.values["status"] == AgentStatus.AWAITING_APPROVAL
    assert snapshot.values["approval_required"] is True
    assert snapshot.values["approval_granted"] is False