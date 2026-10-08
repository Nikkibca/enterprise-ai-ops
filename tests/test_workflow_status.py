
from app.agents.state import AgentStatus
from app.models import Task, TaskStatus
from app.workflow_status import sync_task_status


def test_sync_planning_status(db_session):
    task = Task(
        user_id="test-user",
        request="Test workflow status",
        status=TaskStatus.CREATED.value,
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    updated = sync_task_status(
        db=db_session,
        task=task,
        agent_status=AgentStatus.PLANNING,
    )

    assert updated.status == TaskStatus.PLANNING.value


def test_sync_high_risk_approval_status(db_session):
    task = Task(
        user_id="test-user",
        request="Test workflow approval",
        status=TaskStatus.PLANNING.value,
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    updated = sync_task_status(
        db=db_session,
        task=task,
        agent_status=AgentStatus.AWAITING_APPROVAL,
    )

    assert updated.status == TaskStatus.AWAITING_APPROVAL.value


def test_execution_states_map_to_executing(db_session):
    task = Task(
        user_id="test-user",
        request="Test workflow execution",
        status=TaskStatus.AWAITING_APPROVAL.value,
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    updated = sync_task_status(
        db=db_session,
        task=task,
        agent_status=AgentStatus.EXECUTING_ACTION,
    )

    assert updated.status == TaskStatus.EXECUTING.value


def test_verifying_status(db_session):
    task = Task(
        user_id="test-user",
        request="Test workflow verification",
        status=TaskStatus.EXECUTING.value,
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    updated = sync_task_status(
        db=db_session,
        task=task,
        agent_status=AgentStatus.VERIFYING,
    )

    assert updated.status == TaskStatus.VERIFYING.value


def test_completed_status(db_session):
    task = Task(
        user_id="test-user",
        request="Test workflow completion",
        status=TaskStatus.VERIFYING.value,
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    updated = sync_task_status(
        db=db_session,
        task=task,
        agent_status=AgentStatus.COMPLETED,
    )

    assert updated.status == TaskStatus.COMPLETED.value


def test_failed_status(db_session):
    task = Task(
        user_id="test-user",
        request="Test workflow failure",
        status=TaskStatus.PLANNING.value,
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    updated = sync_task_status(
        db=db_session,
        task=task,
        agent_status=AgentStatus.FAILED,
    )

    assert updated.status == TaskStatus.FAILED.value


def test_idle_does_not_change_task_status(db_session):
    task = Task(
        user_id="test-user",
        request="Test idle workflow",
        status=TaskStatus.CREATED.value,
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    updated = sync_task_status(
        db=db_session,
        task=task,
        agent_status=AgentStatus.IDLE,
    )

    assert updated.status == TaskStatus.CREATED.value

