"""Verdict backend configuration package.

Exports the Settings singleton and domain-aware configuration utilities.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    groq_api_key: str = ""  # Set via GROQ_API_KEY env var
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://verdict.up.railway.app",
    ]
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
