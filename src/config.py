"""Application configuration management.

This module handles all configuration settings using pydantic-settings
for type-safe environment variable loading.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings can be overridden via environment variables.
    For local development, create a .env file in the project root.
    """

    # Application
    app_name: str = "AI Tutor API"
    app_version: str = "0.1.0"
    debug: bool = False

    # API Configuration
    api_v1_prefix: str = "/api/v1"

    # CORS Settings
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"]

    # AI Model Configuration
    model_name: Optional[str] = None
    model_temperature: float = 0.7
    max_tokens: int = 1000

    # Security
    api_key: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Global settings instance
settings = Settings()
