from app.agents.state import AgentState, AgentStatus
from app.llm.base import LLMProvider


def planning_node(
    state: AgentState,
    llm_provider: LLMProvider,
) -> AgentState:
    request = state["request"]

    agent_plan = llm_provider.create_plan(request)

    return {
        "status": AgentStatus.PLANNING,
        "planning_steps": [
            f"Understand the operational request: {request}",
            "Determine which approved tool is required",
            "Execute the tool and verify the result",
        ],
        "agent_plan": agent_plan,
        "selected_tool": agent_plan.tool_call.tool,
        "tool_arguments": agent_plan.tool_call.arguments,
    }
