from openai import OpenAI
from pydantic import BaseModel, Field

from app.agents.schemas import AgentPlan, ToolCall
from app.llm.settings import LLMSettings


class OpenAIToolArguments(BaseModel):
    query: str = Field(
        description="Query or question to provide to the selected tool."
    )


class OpenAIToolCall(BaseModel):
    tool: str = Field(
        description="Name of the tool the model wants to invoke."
    )
    arguments: OpenAIToolArguments


class OpenAIPlanResponse(BaseModel):
    reasoning_summary: str = Field(
        description="Brief explanation of why the selected tool is appropriate."
    )
    tool_call: OpenAIToolCall


def convert_openai_plan(
    response: OpenAIPlanResponse,
) -> AgentPlan:
    return AgentPlan(
        reasoning_summary=response.reasoning_summary,
        tool_call=ToolCall(
            tool=response.tool_call.tool,
            arguments={
                "query": response.tool_call.arguments.query,
            },
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
    ) -> AgentPlan:
        response = self.client.responses.parse(
            model=self.settings.openai_model,
            instructions=(
                "You are an enterprise operations planning assistant. "
                "Select exactly one tool for the user's request. "
                "The available tools are knowledge.search and sql.read. "
                "Return a concise rationale and the selected tool "
                "with its query argument. "
                "Do not execute tools."
            ),
            input=request,
            text_format=OpenAIPlanResponse,
        )

        parsed = response.output_parsed

        if parsed is None:
            raise ValueError(
                "OpenAI returned no structured plan."
            )

        return convert_openai_plan(parsed)