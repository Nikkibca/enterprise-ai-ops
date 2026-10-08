from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    openai_api_key: str
    openai_model: str
    langgraph_checkpoint_database_url: str
    project1_base_url: str = "http://127.0.0.1:8000"

    # Defaults to OpenAI so the existing test suite continues
    # to expect OpenAIProvider unless explicitly overridden.
    llm_provider: str = "openai"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )