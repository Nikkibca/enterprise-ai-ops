from app.llm.openai_provider import OpenAIProvider
from app.llm.settings import LLMSettings


settings = LLMSettings()
provider = OpenAIProvider(settings)

plan = provider.create_plan(
    "Why did payment failures increase yesterday?"
)

print("Tool:", plan.tool_call.tool)
print("Arguments:", plan.tool_call.arguments)
print("Reasoning summary:", plan.reasoning_summary)
