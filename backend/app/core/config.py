"""Application configuration management using Pydantic Settings."""

from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Core settings and environment configuration."""

    # Project metadata
    PROJECT_NAME: str = "Lenny Growth Assistant API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/lenny_growth",
        description="PostgreSQL connection string",
    )

    # Ollama settings
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Base URL for local Ollama daemon",
    )
    OLLAMA_DEFAULT_MODEL: str = Field(
        default="llama3.2",
        description="Default model for Ollama generation",
    )
    OLLAMA_EMBED_MODEL: str = Field(
        default="nomic-embed-text",
        description="Embedding model for Ollama",
    )
    OLLAMA_TIMEOUT_SECONDS: float = Field(
        default=15.0,
        description="Timeout in seconds for Ollama API requests",
    )

    # Anthropic settings
    ANTHROPIC_API_KEY: Optional[str] = Field(
        default=None,
        description="API key for Anthropic Claude",
    )
    ANTHROPIC_DEFAULT_MODEL: str = Field(
        default="claude-3-5-sonnet-latest",
        description="Default model for Anthropic generation",
    )

    # General LLM defaults
    DEFAULT_PROVIDER: str = Field(
        default="ollama",
        description="Default LLM provider: 'ollama' or 'anthropic'",
    )

    # RAG Retrieval parameters
    SIMILARITY_THRESHOLD: float = Field(
        default=0.65,
        description="Minimum cosine similarity cutoff for grounding citations",
    )
    RETRIEVAL_TOP_K: int = Field(
        default=5,
        description="Top K chunks retrieved per query",
    )

    # CORS origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


settings = Settings()
