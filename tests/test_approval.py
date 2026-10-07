from app.approval import (
    ApprovalDecision,
    approve_task,
    create_approval_request,
    reject_task,
)


def test_create_approval_request():
    request = create_approval_request(
        task_id=42,
        tool_name="service.restart",
        risk_level="high",
        requested_by="user-123",
        reason="High-risk operation requires human approval.",
    )

    assert request.task_id == 42
    assert request.tool_name == "service.restart"
    assert request.risk_level == "high"
    assert request.requested_by == "user-123"
    assert request.reason == (
        "High-risk operation requires human approval."
    )
    assert request.requested_at is not None


def test_approve_task():
    result = approve_task(
        task_id=42,
        decided_by="manager-456",
    )

    assert result.task_id == 42
    assert result.decision == ApprovalDecision.APPROVED
    assert result.decided_by == "manager-456"
    assert result.decided_at is not None


def test_reject_task():
    result = reject_task(
        task_id=42,
        decided_by="manager-456",
    )

    assert result.task_id == 42
    assert result.decision == ApprovalDecision.REJECTED
    assert result.decided_by == "manager-456"
    assert result.decided_at is not None