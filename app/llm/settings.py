from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    langgraph_checkpoint_database_url: str = (
        "postgresql://app_user:app_password@127.0.0.1:5433/enterprise_ai_ops"
    )
    project1_base_url: str = "http://127.0.0.1:8000"

    llm_provider: str = "fake"

    @field_validator("langgraph_checkpoint_database_url", mode="before")
    @classmethod
    def normalize_checkpoint_url(cls, value: str) -> str:
        if isinstance(value, str):
            # Normalize localhost:5433 to 127.0.0.1:5433 to prevent 120s IPv6 timeouts on Windows
            return value.replace("@localhost:5433", "@127.0.0.1:5433")
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )