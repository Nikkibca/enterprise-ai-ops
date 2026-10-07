from app.models import TaskStatus


ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.CREATED: {
        TaskStatus.PLANNING,
        TaskStatus.REJECTED,
    },
    TaskStatus.PLANNING: {
        TaskStatus.AWAITING_APPROVAL,
        TaskStatus.EXECUTING,
        TaskStatus.FAILED,
        TaskStatus.REJECTED,
    },
    TaskStatus.AWAITING_APPROVAL: {
        TaskStatus.EXECUTING,
        TaskStatus.REJECTED,
    },
    TaskStatus.EXECUTING: {
        TaskStatus.VERIFYING,
        TaskStatus.FAILED,
    },
    TaskStatus.VERIFYING: {
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
    },
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.REJECTED: set(),
}


class InvalidTaskTransition(Exception):
    pass


def transition_task(
    current_status: TaskStatus,
    new_status: TaskStatus,
) -> TaskStatus:
    allowed = ALLOWED_TRANSITIONS[current_status]

    if new_status not in allowed:
        raise InvalidTaskTransition(
            f"Invalid task transition: "
            f"{current_status.value} -> {new_status.value}"
        )

    return new_status
