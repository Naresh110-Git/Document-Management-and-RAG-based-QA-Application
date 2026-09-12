"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the backend service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Document Management RAG API"
    app_version: str = "0.1.0"
    environment: Literal["local", "development", "staging", "production", "test"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://rag_user:rag_password@localhost:5432/rag_db"
    db_pool_size: int = Field(default=10, ge=1)
    db_max_overflow: int = Field(default=20, ge=0)

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, ge=1)
    refresh_token_expire_days: int = Field(default=7, ge=1)
    bcrypt_rounds: int = Field(default=12, ge=12, le=15)

    upload_dir: Path = Path("uploads")
    max_upload_size_mb: int = Field(default=25, ge=1)
    allowed_upload_types: list[str] = ["application/pdf"]

    chunk_size: int = Field(default=1000, ge=100)
    chunk_overlap: int = Field(default=200, ge=0)
    retrieval_top_k: int = Field(default=5, ge=1)

    active_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    vector_store_backend: Literal["pgvector", "faiss"] = "pgvector"

    llm_provider: Literal["ollama", "openai", "huggingface"] = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    huggingface_api_key: str | None = None
    huggingface_model: str = "mistralai/Mistral-7B-Instruct-v0.3"

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_dir: Path = Path("logs")
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    rate_limit_requests: int = Field(default=60, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)

    background_worker_count: int = Field(default=2, ge=1)
    background_queue_size: int = Field(default=100, ge=1)

    cache_ttl_seconds: int = Field(default=300, ge=0)
    cache_max_items: int = Field(default=500, ge=1)

    @field_validator("allowed_upload_types", "cors_origins", mode="before")
    @classmethod
    def split_csv_values(cls, value: str | list[str]) -> list[str]:
        """Allow comma-separated environment values for list settings."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def validate_runtime_settings(self) -> "Settings":
        """Validate settings that depend on multiple fields."""
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")

        if self.environment == "production" and self.jwt_secret_key == "change-me-in-production":
            raise ValueError("JWT_SECRET_KEY must be set to a secure value in production")

        return self

    @property
    def max_upload_size_bytes(self) -> int:
        """Return the upload size limit in bytes."""
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
