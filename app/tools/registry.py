from dataclasses import dataclass
from typing import Any, Callable, Type

from pydantic import BaseModel, ValidationError


class ToolExecutionError(Exception):
    pass


ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    risk_level: str
    required_permission: str
    argument_model: Type[BaseModel]
    handler: ToolHandler

    @property
    def argument_schema(self) -> dict[str, Any]:
        return self.argument_model.model_json_schema()

    def to_llm_definition(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "risk_level": self.risk_level,
            "required_permission": self.required_permission,
            "parameters": self.argument_schema,
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        handler: ToolHandler,
        *,
        argument_model: Type[BaseModel],
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
            argument_model=argument_model,
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

    def validate_arguments(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        tool = self.get(name)

        try:
            validated = tool.argument_model.model_validate(
                arguments
            )
        except ValidationError as exc:
            raise ToolExecutionError(
                f"Invalid arguments for tool "
                f"'{name}': {exc}"
            ) from exc

        return validated.model_dump()

    def execute(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        tool = self.get(name)

        validated_arguments = self.validate_arguments(
            name,
            arguments,
        )

        return tool.handler(validated_arguments)

    def list_tools(self) -> list[str]:
        return sorted(self._tools.keys())

    def list_definitions(self) -> list[ToolDefinition]:
        return [
            self._tools[name]
            for name in sorted(self._tools)
        ]

    def build_llm_catalog(self) -> list[dict[str, Any]]:
        return [
            definition.to_llm_definition()
            for definition in self.list_definitions()
        ]