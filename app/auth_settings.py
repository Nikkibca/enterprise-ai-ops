from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "enterprise-ai-ops"
    jwt_audience: str = "enterprise-ai-ops-api"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )