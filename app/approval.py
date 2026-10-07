from dataclasses import dataclass
from datetime import datetime, timezone


class ApprovalDecision:
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ApprovalRequest:
    task_id: int
    tool_name: str
    risk_level: str
    requested_by: str
    requested_at: datetime
    reason: str


@dataclass(frozen=True)
class ApprovalResult:
    task_id: int
    decision: str
    decided_by: str
    decided_at: datetime


def create_approval_request(
    task_id: int,
    tool_name: str,
    risk_level: str,
    requested_by: str,
    reason: str,
) -> ApprovalRequest:
    return ApprovalRequest(
        task_id=task_id,
        tool_name=tool_name,
        risk_level=risk_level,
        requested_by=requested_by,
        requested_at=datetime.now(timezone.utc),
        reason=reason,
    )


def approve_task(
    task_id: int,
    decided_by: str,
) -> ApprovalResult:
    return ApprovalResult(
        task_id=task_id,
        decision=ApprovalDecision.APPROVED,
        decided_by=decided_by,
        decided_at=datetime.now(timezone.utc),
    )


def reject_task(
    task_id: int,
    decided_by: str,
) -> ApprovalResult:
    return ApprovalResult(
        task_id=task_id,
        decision=ApprovalDecision.REJECTED,
        decided_by=decided_by,
        decided_at=datetime.now(timezone.utc),
    )