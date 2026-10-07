from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.approval_service import (
    ApprovalNotFoundError,
    InvalidApprovalStateError,
    approve_request,
    create_approval,
    get_approval,
    reject_request,
)
from app.dependencies import (
    get_checkpointer,
    get_db,
    get_llm_provider,
)

from app.models import Task
from app.schemas import (
    ApprovalDecisionRequest,
    ApprovalResponse,
    CreateApprovalRequest,
    CreateTaskRequest,
    TaskResponse,
    TransitionTaskRequest,
)
from app.task_creation import create_task
from app.task_service import InvalidTaskTransition
from app.task_service_db import update_task_status
from app.workflow_runner import WorkflowRunner
from app.workflow_service import start_task_workflow

router = APIRouter()


@router.post("/tasks", response_model=TaskResponse)
def create_task_endpoint(
    payload: CreateTaskRequest,
    db: Session = Depends(get_db),
    llm_provider=Depends(get_llm_provider),
    checkpointer=Depends(get_checkpointer),
):
    task = create_task(
        db=db,
        user_id=payload.user_id,
        request=payload.request,
        actor=payload.user_id,
    )

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

    db.refresh(task)

    return task


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
):
    task = db.get(Task, task_id)

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    return task


@router.post(
    "/tasks/{task_id}/transition",
    response_model=TaskResponse,
)
def transition_task_endpoint(
    task_id: int,
    payload: TransitionTaskRequest,
    db: Session = Depends(get_db),
):
    task = db.get(Task, task_id)

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    try:
        return update_task_status(
            db,
            task,
            payload.status,
            actor="api",
        )
    except InvalidTaskTransition as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc


@router.post(
    "/approvals",
    response_model=ApprovalResponse,
    status_code=201,
)
def create_approval_endpoint(
    payload: CreateApprovalRequest,
    db: Session = Depends(get_db),
):
    task = db.get(Task, payload.task_id)

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    return create_approval(
        db=db,
        task_id=payload.task_id,
        tool_name=payload.tool_name,
        risk_level=payload.risk_level,
        requested_by=payload.requested_by,
        reason=payload.reason,
    )


@router.get(
    "/approvals/{approval_id}",
    response_model=ApprovalResponse,
)
def get_approval_endpoint(
    approval_id: int,
    db: Session = Depends(get_db),
):
    try:
        return get_approval(
            db=db,
            approval_id=approval_id,
        )
    except ApprovalNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.post(
    "/approvals/{approval_id}/approve",
    response_model=ApprovalResponse,
)
def approve_approval_endpoint(
    approval_id: int,
    payload: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
):
    try:
        return approve_request(
            db=db,
            approval_id=approval_id,
            decided_by=payload.decided_by,
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


@router.post(
    "/approvals/{approval_id}/reject",
    response_model=ApprovalResponse,
)
def reject_approval_endpoint(
    approval_id: int,
    payload: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
):
    try:
        return reject_request(
            db=db,
            approval_id=approval_id,
            decided_by=payload.decided_by,
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