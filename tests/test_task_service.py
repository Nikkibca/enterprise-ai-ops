import pytest

from app.models import TaskStatus
from app.task_service import InvalidTaskTransition, transition_task


def test_created_can_move_to_planning():
    result = transition_task(
        TaskStatus.CREATED,
        TaskStatus.PLANNING,
    )

    assert result == TaskStatus.PLANNING


def test_planning_can_require_approval():
    result = transition_task(
        TaskStatus.PLANNING,
        TaskStatus.AWAITING_APPROVAL,
    )

    assert result == TaskStatus.AWAITING_APPROVAL


def test_executing_can_move_to_verifying():
    result = transition_task(
        TaskStatus.EXECUTING,
        TaskStatus.VERIFYING,
    )

    assert result == TaskStatus.VERIFYING


def test_verifying_can_complete():
    result = transition_task(
        TaskStatus.VERIFYING,
        TaskStatus.COMPLETED,
    )

    assert result == TaskStatus.COMPLETED


def test_completed_cannot_move_back_to_planning():
    with pytest.raises(InvalidTaskTransition):
        transition_task(
            TaskStatus.COMPLETED,
            TaskStatus.PLANNING,
        )


def test_created_cannot_execute_directly():
    with pytest.raises(InvalidTaskTransition):
        transition_task(
            TaskStatus.CREATED,
            TaskStatus.EXECUTING,
        )
