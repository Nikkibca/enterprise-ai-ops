import os

from langgraph.checkpoint.postgres import PostgresSaver

from app.agents.schemas import AgentPlan
from app.agents.state import AgentStatus
from app.approval_service import approve_request
from app.llm.fake import FakeLLMProvider
from app.models import Task
from app.workflow_runner import WorkflowRunner


DATABASE_URL = os.getenv(
    "LANGGRAPH_CHECKPOINT_DATABASE_URL",
    "postgresql://app_user:app_password@localhost:5433/enterprise_ai_ops",
)


def test_high_risk_workflow_survives_postgres_checkpoint(
    db_session,
):
    plan = AgentPlan(
        reasoning_summary="Restart the payment worker.",
        tool_call={
            "tool": "service.restart",
            "arguments": {
                "service": "payment-worker",
            },
        },
    )

    task = Task(
        user_id="manager-123",
        request="Restart the payment worker",
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    thread_id = f"durable-test-task-{task.id}"

    with PostgresSaver.from_conn_string(
        DATABASE_URL
    ) as checkpointer:
        checkpointer.setup()

        runner = WorkflowRunner(
            FakeLLMProvider(plan),
            db=db_session,
            checkpointer=checkpointer,
        )

        initial_state = {
            "task_id": task.id,
            "user_id": task.user_id,
            "request": task.request,
            "status": AgentStatus.IDLE,
        }

        # ---------------------------------------------------------
        # 1. Start the high-risk workflow.
        # ---------------------------------------------------------

        first_result = runner.start(
            initial_state,
            thread_id=thread_id,
        )

        assert "__interrupt__" in first_result

        approval_id = first_result["approval_id"]

        assert approval_id is not None
        assert (
            first_result["status"]
            == AgentStatus.AWAITING_APPROVAL
        )

        # ---------------------------------------------------------
        # 2. Verify the workflow state was persisted.
        # ---------------------------------------------------------

        config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }

        checkpoint = checkpointer.get(config)

        assert checkpoint is not None

        snapshot = runner.graph.get_state(config)

        assert (
            snapshot.values["status"]
            == AgentStatus.AWAITING_APPROVAL
        )

        assert snapshot.values["approval_required"] is True
        assert snapshot.values["approval_granted"] is False

        # ---------------------------------------------------------
        # 3. Simulate the process being stopped.
        #
        #    The runner/checkpointer context is closed here.
        #    The checkpoint remains in PostgreSQL.
        # ---------------------------------------------------------

    # -------------------------------------------------------------
    # 4. Approve the pending operational action.
    # -------------------------------------------------------------

    approval = approve_request(
        db=db_session,
        approval_id=approval_id,
        decided_by="test-manager",
    )

    assert approval.status == "approved"
    assert approval.decided_by == "test-manager"

    # -------------------------------------------------------------
    # 5. Re-open the PostgreSQL checkpointer.
    #
    #    This simulates a new application process recovering the
    #    workflow from the persisted checkpoint.
    # -------------------------------------------------------------

    with PostgresSaver.from_conn_string(
        DATABASE_URL
    ) as checkpointer:
        checkpointer.setup()

        recovered_checkpoint = checkpointer.get(
            {
                "configurable": {
                    "thread_id": thread_id,
                }
            }
        )

        assert recovered_checkpoint is not None

        runner = WorkflowRunner(
            FakeLLMProvider(plan),
            db=db_session,
            checkpointer=checkpointer,
        )

        # ---------------------------------------------------------
        # 6. Resume the exact same workflow thread.
        # ---------------------------------------------------------

        final_result = runner.resume(
            thread_id=thread_id,
            approved=True,
        )

        assert (
            final_result["status"]
            == AgentStatus.COMPLETED
        )

        assert final_result["approval_granted"] is True

        assert (
            final_result["tool_result"]["tool"]
            == "service.restart"
        )

        assert (
            final_result["tool_result"]["status"]
            == "simulated"
        )

        assert (
            final_result["tool_result"]["service"]
            == "payment-worker"
        )

        # ---------------------------------------------------------
        # 7. Verify the persisted workflow reached completion.
        # ---------------------------------------------------------

        final_snapshot = runner.graph.get_state(
            {
                "configurable": {
                    "thread_id": thread_id,
                }
            }
        )

        assert (
            final_snapshot.values["status"]
            == AgentStatus.COMPLETED
        )