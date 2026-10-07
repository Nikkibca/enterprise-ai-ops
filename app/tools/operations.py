from typing import Any


def service_restart(arguments: dict[str, Any]) -> dict[str, Any]:
    service = arguments.get("service")

    if not service:
        raise ValueError("service.restart requires a service.")

    return {
        "tool": "service.restart",
        "status": "simulated",
        "service": service,
        "message": f"Simulated restart of service: {service}",
    }