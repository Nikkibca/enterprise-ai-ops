from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    openai_api_key: str
    openai_model: str
    langgraph_checkpoint_database_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )