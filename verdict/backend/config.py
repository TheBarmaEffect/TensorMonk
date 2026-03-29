"""Verdict backend configuration."""

from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    groq_api_key: str = "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"
    redis_url: str = "redis://localhost:6379"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://verdict.up.railway.app",
    ]
    demo_mode: bool = False
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
