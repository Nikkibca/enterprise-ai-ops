from collections import deque

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.types import Command
from sqlalchemy.orm import Session

from app.agents.graph import build_agent_graph
from app.agents.state import AgentState, AgentStatus
from app.llm.base import LLMProvider
from app.models import Task, TaskStatus
from app.task_service import ALLOWED_TRANSITIONS
from app.task_service_db import update_task_status


class WorkflowRunner:
    def __init__(
        self,
        llm_provider: LLMProvider,
        db: Session | None = None,
        checkpointer: BaseCheckpointSaver | None = None,
    ):
        self.llm_provider = llm_provider
        self.db = db
        self.checkpointer = checkpointer

        self.graph = build_agent_graph(
            llm_provider,
            db=db,
            checkpointer=checkpointer,
        )

    def get_state(
        self,
        *,
        thread_id: str,
    ) -> AgentState:
        """
        Retrieve the latest persisted LangGraph state for a workflow.

        The selected tool and other workflow-specific values live in
        the LangGraph checkpoint rather than the SQL Task record.
        """
        config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }

        snapshot = self.graph.get_state(config)

        return dict(snapshot.values)

    def _persist_workflow_status(
        self,
        state: AgentState,
    ) -> None:
        if self.db is None:
            return

        task_id = state.get("task_id")

        if task_id is None:
            return

        workflow_status = state.get("status")

        if workflow_status is None:
            return

        # LangGraph may return enum instances during direct execution
        # and plain strings after checkpoint serialization/resumption.
        if isinstance(workflow_status, TaskStatus):
            target_status = workflow_status
        else:
            status_value = getattr(
                workflow_status,
                "value",
                workflow_status,
            )
            target_status = TaskStatus(status_value)

        task = self.db.get(Task, task_id)

        if task is None:
            raise ValueError(
                f"Task not found for workflow: {task_id}"
            )

        current_status = TaskStatus(task.status)

        if current_status == target_status:
            return

        if current_status in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.REJECTED,
        }:
            return

        path = self._find_transition_path(
            current_status,
            target_status,
        )

        if path is None:
            raise ValueError(
                "No valid task-status transition path exists: "
                f"{current_status.value} -> "
                f"{target_status.value}"
            )

        for next_status in path:
            task = update_task_status(
                db=self.db,
                task=task,
                new_status=next_status,
                actor=state.get("user_id", "system"),
            )

    @staticmethod
    def _find_transition_path(
        start: TaskStatus,
        target: TaskStatus,
    ) -> list[TaskStatus] | None:
        """
        Find a valid path through the deterministic task state machine.

        This allows the workflow runner to reconcile a persisted Task
        with the final LangGraph state without bypassing transition
        validation.
        """
        queue: deque[
            tuple[TaskStatus, list[TaskStatus]]
        ] = deque([(start, [])])

        visited: set[TaskStatus] = {start}

        while queue:
            current, path = queue.popleft()

            for next_status in ALLOWED_TRANSITIONS[current]:
                if next_status in visited:
                    continue

                next_path = [
                    *path,
                    next_status,
                ]

                if next_status == target:
                    return next_path

                visited.add(next_status)
                queue.append(
                    (next_status, next_path)
                )

        return None

    def start(
        self,
        state: AgentState,
        *,
        thread_id: str,
    ) -> AgentState:
        config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }

        try:
            result = self.graph.invoke(
                state,
                config,
            )
        except Exception:
            failed_state = {
                **state,
                "status": AgentStatus.FAILED,
            }

            self._persist_workflow_status(failed_state)

            raise

        self._persist_workflow_status(result)

        return result

    def resume(
        self,
        *,
        thread_id: str,
        approved: bool = True,
        decided_by: str | None = None,
    ) -> AgentState:
        config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }

        if decided_by is not None:
            resume_value = {
                "approved": approved,
                "decided_by": decided_by,
            }
        else:
            resume_value = approved

        try:
            result = self.graph.invoke(
                Command(resume=resume_value),
                config,
            )
        except Exception:
            current_state = self.get_state(
                thread_id=thread_id,
            )

            failed_state = {
                **current_state,
                "status": AgentStatus.FAILED,
            }

            self._persist_workflow_status(failed_state)

            raise

        self._persist_workflow_status(result)

        return result