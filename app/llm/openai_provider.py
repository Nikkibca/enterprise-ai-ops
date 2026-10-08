from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field

from app.agents.schemas import AgentPlan, ToolCall
from app.llm.settings import LLMSettings
from app.tools.factory import create_tool_registry
from app.tools.registry import ToolRegistry


class OpenAIToolArguments(BaseModel):
    query: str | None = Field(
        default=None,
        description=(
            "Query or question for a selected knowledge or "
            "SQL tool."
        ),
    )
    top_k: int | None = Field(
        default=None,
        description=(
            "Maximum number of knowledge results to retrieve."
        ),
    )
    operation: str | None = Field(
        default=None,
        description=(
            "Approved analytics operation."
        ),
    )
    values: list[float] | None = Field(
        default=None,
        description=(
            "Numeric values for numerical analysis."
        ),
    )
    service: str | None = Field(
        default=None,
        description=(
            "Name of the operational service."
        ),
    )


class OpenAIToolCall(BaseModel):
    tool: str = Field(
        description=(
            "Name of the approved tool to invoke."
        ),
    )
    arguments: OpenAIToolArguments


class OpenAIPlanResponse(BaseModel):
    reasoning_summary: str = Field(
        description=(
            "Brief explanation of why the selected tool "
            "is appropriate."
        ),
    )
    tool_call: OpenAIToolCall


def convert_openai_plan(
    response: OpenAIPlanResponse,
) -> AgentPlan:
    arguments: dict[str, Any] = {}

    raw_arguments = response.tool_call.arguments.model_dump(
        exclude_none=True,
    )

    arguments.update(raw_arguments)

    return AgentPlan(
        reasoning_summary=response.reasoning_summary,
        tool_call=ToolCall(
            tool=response.tool_call.tool,
            arguments=arguments,
        ),
    )


class OpenAIProvider:
    def __init__(
        self,
        settings: LLMSettings,
    ):
        self.settings = settings
        self.client = OpenAI(
            api_key=settings.openai_api_key,
        )

    def create_plan(
        self,
        request: str,
        tool_registry: ToolRegistry | None = None,
    ) -> AgentPlan:
        if tool_registry is None:
            tool_registry = create_tool_registry()

        tool_catalog = tool_registry.build_llm_catalog()

        instructions = (
            "You are an enterprise operations planning assistant.\n\n"
            "Your job is to select exactly one tool from the "
            "approved tool catalog for the user's request.\n\n"
            "Available tools are provided below as structured "
            "metadata. Use the tool name, description, risk level, "
            "required permission, and parameter schema to choose "
            "the most appropriate tool.\n\n"
            f"TOOL CATALOG:\n{tool_catalog}\n\n"
            "Rules:\n"
            "1. Select exactly one tool from the catalog.\n"
            "2. Never invent a tool name.\n"
            "3. Never invent parameters that are not supported "
            "by the selected tool.\n"
            "4. Return only a structured plan.\n"
            "5. Do not execute tools.\n"
            "6. Do not claim that a tool was executed.\n"
            "7. For high-risk operations, selecting the tool does "
            "not mean the operation is authorized. A separate "
            "deterministic policy engine and human approval "
            "workflow control execution.\n"
        )

        response = self.client.responses.parse(
            model=self.settings.openai_model,
            instructions=instructions,
            input=request,
            text_format=OpenAIPlanResponse,
        )

        parsed = response.output_parsed

        if parsed is None:
            raise ValueError(
                "OpenAI returned no structured plan."
            )

        return convert_openai_plan(parsed)