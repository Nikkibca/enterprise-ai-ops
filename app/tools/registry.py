from dataclasses import dataclass
from typing import Any, Callable


class ToolExecutionError(Exception):
    pass


ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    risk_level: str
    required_permission: str
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        handler: ToolHandler,
        *,
        description: str = "",
        risk_level: str = "low",
        required_permission: str = "tool.execute",
    ) -> None:
        if name in self._tools:
            raise ToolExecutionError(
                f"Tool already registered: {name}"
            )

        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            risk_level=risk_level,
            required_permission=required_permission,
            handler=handler,
        )

    def is_registered(self, name: str) -> bool:
        return name in self._tools

    def get(self, name: str) -> ToolDefinition:
        tool = self._tools.get(name)

        if tool is None:
            raise ToolExecutionError(
                f"Tool not registered: {name}"
            )

        return tool

    def execute(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        tool = self.get(name)
        return tool.handler(arguments)

    def list_tools(self) -> list[str]:
        return sorted(self._tools.keys())

    def list_definitions(self) -> list[ToolDefinition]:
        return [
            self._tools[name]
            for name in sorted(self._tools)
        ]