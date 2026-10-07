import pytest

from app.tools.operations import service_restart


def test_service_restart_returns_simulated_success():
    result = service_restart(
        {
            "service": "payment-worker",
        }
    )

    assert result["tool"] == "service.restart"
    assert result["status"] == "simulated"
    assert result["service"] == "payment-worker"


def test_service_restart_requires_service():
    with pytest.raises(ValueError, match="requires a service"):
        service_restart({})