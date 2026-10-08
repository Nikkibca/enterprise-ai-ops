
from datetime import datetime

from pydantic import BaseModel

from app.models import ApprovalStatus, TaskStatus


class CreateTaskRequest(BaseModel):
    request: str


class TaskResponse(BaseModel):
    id: int
    user_id: str
    request: str
    status: TaskStatus


class TransitionTaskRequest(BaseModel):
    status: TaskStatus


class CreateApprovalRequest(BaseModel):
    task_id: int
    tool_name: str
    risk_level: str
    reason: str


class ApprovalResponse(BaseModel):
    id: int
    task_id: int
    tool_name: str
    risk_level: str
    requested_by: str
    reason: str
    status: ApprovalStatus
    requested_at: datetime
    decided_by: str | None = None
    decided_at: datetime | None = None


class ApprovalDecisionRequest(BaseModel):
    pass

