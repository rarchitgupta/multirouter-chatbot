from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/llm_db"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    max_conversation_history: int = 20
    cors_origins: list[str] = ["http://localhost:3000"]

    # LLM providers
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""

    # Ingestion
    redis_stream_name: str = "inference_logs"
    redis_stream_maxlen: int = 100_000
    ingestion_consumer_group: str = "ingestion"
    ingestion_retry_after_ms: int = 30_000


settings = Settings()
