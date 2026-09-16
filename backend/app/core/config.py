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
        default="glm-5.3-flash",
        description="Default model for Ollama generation",
    )
    OLLAMA_EMBED_MODEL: str = Field(
        default="nomic-embed-text",
        description="Embedding model for Ollama",
    )
    OLLAMA_TIMEOUT_SECONDS: float = Field(
        default=120.0,
        description="Timeout in seconds for Ollama API requests",
    )

    # Anthropic settings
    ANTHROPIC_API_KEY: Optional[str] = Field(
        default=None,
        description="API key for Anthropic Claude",
    )
    ANTHROPIC_WORKSPACE_ID: Optional[str] = Field(
        default=None,
        description="Workspace ID for org-level Anthropic API keys",
    )
    ANTHROPIC_DEFAULT_MODEL: str = Field(
        default="claude-sonnet-5-latest",
        description="Default model for Anthropic generation",
    )

    # Google Gemini settings
    GEMINI_API_KEY: Optional[str] = Field(
        default=None,
        description="API key for Google Gemini",
    )
    GEMINI_DEFAULT_MODEL: str = Field(
        default="gemini-flash-latest",
        description="Default model for Google Gemini",
    )

    # Groq settings (Ultra-fast 500 tokens/sec)
    GROQ_API_KEY: Optional[str] = Field(
        default=None,
        description="API key for Groq Cloud",
    )
    GROQ_DEFAULT_MODEL: str = Field(
        default="openai/gpt-oss-120b",
        description="Default model for Groq",
    )

    # OpenAI settings
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="API key for OpenAI",
    )
    OPENAI_DEFAULT_MODEL: str = Field(
        default="gpt-4o-mini",
        description="Default model for OpenAI",
    )

    # General LLM defaults
    DEFAULT_PROVIDER: str = Field(
        default="ollama",
        description="Default LLM provider: 'ollama', 'gemini', 'groq', 'openai', or 'anthropic'",
    )

    # RAG Retrieval parameters
    SIMILARITY_THRESHOLD: float = Field(
        default=0.48,
        description="Minimum cosine similarity cutoff for grounding citations",
    )
    RETRIEVAL_TOP_K: int = Field(
        default=3,
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
