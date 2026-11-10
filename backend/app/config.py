"""
Application configuration using pydantic-settings.
Loads all environment variables with sensible defaults.
"""

from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./test.db"

    # JWT Authentication
    # Set a unique value in backend/.env. Never ship a shared signing key.
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440  # 24 hours

    # Gnani Prisma (Speech-to-Text)
    GNANI_PRISMA_API_KEY: str = ""
    GNANI_PRISMA_API_URL: str = "https://api.vachana.ai/stt/v3"

    # Gnani Evon (LLM / NLP extraction)
    GNANI_EVON_API_KEY: str = ""
    GNANI_EVON_API_URL: str = "https://api.vachana.ai/v1/chat/completions"

    # Gnani Timbre (Text-to-Speech)
    GNANI_TIMBRE_API_KEY: str = ""
    GNANI_TIMBRE_API_URL: str = "https://api.vachana.ai/api/v1/tts/inference"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_cors_origins(cls, v: object) -> List[str]:
        """Split comma-separated CORS origins string into a list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v  # type: ignore[return-value]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


# Singleton settings instance
settings = Settings()


def get_settings() -> Settings:
    """Return the singleton settings instance."""
    return settings
