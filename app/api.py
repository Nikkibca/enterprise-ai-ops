
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agents.state import AgentStatus
from app.approval_service import (
    ApprovalNotFoundError,
    InvalidApprovalStateError,
    approve_request,
    create_approval,
    get_approval,
    reject_request,
)
from app.authentication import (
    AuthenticatedPrincipal,
    get_current_principal,
)
from app.db import SessionLocal
from app.dependencies import (
    get_checkpointer,
    get_llm_provider,
)
from app.models import (
    Task,
    TaskStatus,
    ApprovalStatus,
)
from app.policy.permissions import get_user_permissions
from app.schemas import (
    ApprovalResponse,
    CreateApprovalRequest,
    CreateTaskRequest,
    TaskResponse,
    TransitionTaskRequest,
)
from app.task_service import (
    InvalidTaskTransition,
    transition_task,
)
from app.task_service_db import update_task_status
from app.workflow_runner import WorkflowRunner
from app.workflow_service import start_task_workflow


router = APIRouter()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def _validate_approval_workflow(
    *,
    approval,
    task,
    workflow_runner,
):
    if not task.workflow_thread_id:
        raise HTTPException(
            status_code=409,
            detail=(
                "Cannot act on the approval because the task "
                "does not have a workflow checkpoint."
            ),
        )

    workflow_state = workflow_runner.get_state(
        thread_id=task.workflow_thread_id,
    )

    if workflow_state.get("status") != AgentStatus.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=409,
            detail=(
                "Cannot act on the approval because the workflow "
                "is no longer awaiting approval."
            ),
        )

    checkpoint_approval_id = workflow_state.get("approval_id")

    if checkpoint_approval_id != approval.id:
        raise HTTPException(
            status_code=409,
            detail=(
                "Cannot act on the approval because the workflow "
                "approval does not match the requested approval."
            ),
        )

    selected_tool = workflow_state.get("selected_tool")

    if selected_tool != approval.tool_name:
        raise HTTPException(
            status_code=409,
            detail=(
                "Cannot act on the approval because the workflow "
                "tool does not match the requested approval."
            ),
        )


@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
)
def create_task_endpoint(
    payload: CreateTaskRequest,
    principal: AuthenticatedPrincipal = Depends(
        get_current_principal
    ),
    db: Session = Depends(get_db),
    llm_provider=Depends(get_llm_provider),
    checkpointer=Depends(get_checkpointer),
):
    task = Task(
        user_id=principal.user_id,
        request=payload.request,
        status=TaskStatus.CREATED.value,
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    workflow_runner = WorkflowRunner(
        llm_provider=llm_provider,
        db=db,
        checkpointer=checkpointer,
    )

    start_task_workflow(
        db=db,
        task=task,
        workflow_runner=workflow_runner,
    )

    return task


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
)
def get_task_endpoint(
    task_id: int,
    principal: AuthenticatedPrincipal = Depends(
        get_current_principal
    ),
    db: Session = Depends(get_db),
):
    task = db.get(Task, task_id)

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found.",
        )

    permissions = get_user_permissions(
        principal.user_id
    )

    is_task_owner = task.user_id == principal.user_id
    is_operations_manager = (
        "operations.restart" in permissions
    )

    if not is_task_owner and not is_operations_manager:
        raise HTTPException(
            status_code=403,
            detail="User is not authorized to view this task.",
        )

    return task


@router.post(
    "/tasks/{task_id}/transition",
    response_model=TaskResponse,
)
def transition_task_endpoint(
    task_id: int,
    payload: TransitionTaskRequest,
    principal: AuthenticatedPrincipal = Depends(
        get_current_principal
    ),
    db: Session = Depends(get_db),
):
    task = db.get(Task, task_id)

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found.",
        )

    permissions = get_user_permissions(
        principal.user_id
    )

    is_task_owner = task.user_id == principal.user_id
    is_operations_manager = (
        "operations.restart" in permissions
    )

    if not is_task_owner and not is_operations_manager:
        raise HTTPException(
            status_code=403,
            detail="User is not authorized to transition this task.",
        )

    try:
        new_status = transition_task(
            TaskStatus(task.status),
            payload.status,
        )
    except InvalidTaskTransition as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    task = update_task_status(
        db=db,
        task=task,
        new_status=new_status,
        actor=principal.user_id,
    )

    return task


@router.post(
    "/approvals",
    response_model=ApprovalResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_approval_endpoint(
    payload: CreateApprovalRequest,
    principal: AuthenticatedPrincipal = Depends(
        get_current_principal
    ),
    db: Session = Depends(get_db),
    llm_provider=Depends(get_llm_provider),
    checkpointer=Depends(get_checkpointer),
):
    task = db.get(Task, payload.task_id)

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found.",
        )

    if task.user_id != principal.user_id:
        raise HTTPException(
            status_code=403,
            detail=(
                "User is not authorized to create an approval "
                "for this task."
            ),
        )

    if task.status == TaskStatus.COMPLETED.value:
        raise HTTPException(
            status_code=400,
            detail="Cannot create an approval for a completed task.",
        )

    if not task.workflow_thread_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot create an approval because the task "
                "does not have a workflow checkpoint."
            ),
        )

    workflow_runner = WorkflowRunner(
        llm_provider=llm_provider,
        db=db,
        checkpointer=checkpointer,
    )

    workflow_state = workflow_runner.get_state(
        thread_id=task.workflow_thread_id,
    )

    workflow_status = workflow_state.get("status")

    if workflow_status != AgentStatus.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot create an approval because the workflow "
                "is not awaiting approval."
            ),
        )

    selected_tool = workflow_state.get("selected_tool")

    if selected_tool != payload.tool_name:
        raise HTTPException(
            status_code=400,
            detail=(
                "Approval tool does not match the task's "
                "selected tool."
            ),
        )

    approval = create_approval(
        db=db,
        task_id=payload.task_id,
        tool_name=payload.tool_name,
        risk_level=payload.risk_level,
        requested_by=principal.user_id,
        reason=payload.reason,
    )

    return approval


@router.get(
    "/approvals/{approval_id}",
    response_model=ApprovalResponse,
)
def get_approval_endpoint(
    approval_id: int,
    principal: AuthenticatedPrincipal = Depends(
        get_current_principal
    ),
    db: Session = Depends(get_db),
):
    try:
        approval = get_approval(
            db=db,
            approval_id=approval_id,
        )
    except ApprovalNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    task = db.get(Task, approval.task_id)

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Parent task not found.",
        )

    permissions = get_user_permissions(
        principal.user_id
    )

    is_task_owner = task.user_id == principal.user_id
    is_operations_manager = (
        "operations.restart" in permissions
    )

    if not is_task_owner and not is_operations_manager:
        raise HTTPException(
            status_code=403,
            detail="User is not authorized to view this approval.",
        )

    return approval


@router.post(
    "/approvals/{approval_id}/approve",
    response_model=ApprovalResponse,
)
def approve_approval_endpoint(
    approval_id: int,
    principal: AuthenticatedPrincipal = Depends(
        get_current_principal
    ),
    db: Session = Depends(get_db),
    llm_provider=Depends(get_llm_provider),
    checkpointer=Depends(get_checkpointer),
):
    permissions = get_user_permissions(
        principal.user_id
    )

    if "operations.restart" not in permissions:
        raise HTTPException(
            status_code=403,
            detail=(
                "User does not have permission to approve "
                "operational restart actions."
            ),
        )

    try:
        approval = get_approval(
            db=db,
            approval_id=approval_id,
        )
    except ApprovalNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    task = db.get(Task, approval.task_id)

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Parent task not found.",
        )

    if approval.status != ApprovalStatus.PENDING.value:
        raise HTTPException(
            status_code=409,
            detail="Only pending approval requests can be approved.",
        )

    workflow_runner = WorkflowRunner(
        llm_provider=llm_provider,
        db=db,
        checkpointer=checkpointer,
    )

    _validate_approval_workflow(
        approval=approval,
        task=task,
        workflow_runner=workflow_runner,
    )

    try:
        approval = approve_request(
            db=db,
            approval_id=approval_id,
            decided_by=principal.user_id,
        )
    except ApprovalNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except InvalidApprovalStateError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    workflow_runner.resume(
        thread_id=task.workflow_thread_id,
        approved=True,
        decided_by=principal.user_id,
    )

    return approval


@router.post(
    "/approvals/{approval_id}/reject",
    response_model=ApprovalResponse,
)
def reject_approval_endpoint(
    approval_id: int,
    principal: AuthenticatedPrincipal = Depends(
        get_current_principal
    ),
    db: Session = Depends(get_db),
    llm_provider=Depends(get_llm_provider),
    checkpointer=Depends(get_checkpointer),
):
    permissions = get_user_permissions(
        principal.user_id
    )

    if "operations.restart" not in permissions:
        raise HTTPException(
            status_code=403,
            detail=(
                "User does not have permission to reject "
                "operational restart actions."
            ),
        )

    try:
        approval = get_approval(
            db=db,
            approval_id=approval_id,
        )
    except ApprovalNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    task = db.get(Task, approval.task_id)

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Parent task not found.",
        )

    if approval.status != ApprovalStatus.PENDING.value:
        raise HTTPException(
            status_code=409,
            detail="Only pending approval requests can be rejected.",
        )

    workflow_runner = WorkflowRunner(
        llm_provider=llm_provider,
        db=db,
        checkpointer=checkpointer,
    )

    _validate_approval_workflow(
        approval=approval,
        task=task,
        workflow_runner=workflow_runner,
    )

    try:
        approval = reject_request(
            db=db,
            approval_id=approval_id,
            decided_by=principal.user_id,
        )
    except ApprovalNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except InvalidApprovalStateError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    workflow_runner.resume(
        thread_id=task.workflow_thread_id,
        approved=False,
        decided_by=principal.user_id,
    )

    return approval

