from app.agents.state import AgentState, AgentStatus


def completion_node(state: AgentState) -> AgentState:
    verification_result = state.get("verification_result")

    if not verification_result:
        return {
            "status": AgentStatus.FAILED,
            "error": "Cannot complete without verification",
        }

    if not verification_result.get("verified"):
        return {
            "status": AgentStatus.FAILED,
            "error": "Verification did not succeed",
        }

    return {
        "status": AgentStatus.COMPLETED,
        "final_response": "Task completed successfully.",
    }
