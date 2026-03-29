"""Verdict backend configuration package.

Exports the Settings singleton and domain-aware configuration utilities.

Modules:
    settings: Environment-based configuration via pydantic-settings
    domain_config: Per-domain constitutional overlays from domains.yaml

Environment variables:
    GROQ_API_KEY: Required — Groq API key for LLM inference
    REDIS_URL: Optional — Redis connection string for production checkpointing
    LOG_LEVEL: Optional — Python logging level (default: INFO)
    CORS_ORIGINS: Optional — Comma-separated list of allowed origins
    RATE_LIMIT_RPM: Optional — Rate limit requests per minute (default: 60)
    RATE_LIMIT_BURST: Optional — Rate limit burst capacity (default: 10)
    SESSION_DIR: Optional — Session persistence directory (default: data/sessions)
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Uses pydantic-settings for type-safe configuration with automatic
    .env file loading and environment variable override.

    Attributes:
        groq_api_key: Groq API key for LLM inference (required for pipeline).
        cors_origins: List of allowed CORS origins for the frontend.
        log_level: Python logging level string (DEBUG/INFO/WARNING/ERROR).
    """

    groq_api_key: str = ""  # Set via GROQ_API_KEY env var
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://frontend-phi-ten-83.vercel.app",
        "https://verdict.up.railway.app",
    ]
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
