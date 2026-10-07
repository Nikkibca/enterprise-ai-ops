from app.agents.state import AgentState, AgentStatus


def verification_node(
    state: AgentState,
) -> AgentState:
    tool_result = state.get("tool_result")

    if not tool_result:
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
        return {
            "status": AgentStatus.FAILED,
            "error": (
                "Tool execution did not succeed"
            ),
        }

    return {
        "status": AgentStatus.VERIFYING,
        "verification_result": {
            "verified": True,
            "tool": tool_result.get("tool"),
            "status": tool_result.get("status"),
        },
    }