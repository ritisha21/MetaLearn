"""
backend/core/config.py

Centralised settings — reads from .env via pydantic-settings.
Every environment variable the backend needs is declared here,
not scattered across routers or service files.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API keys
    ANTHROPIC_API_KEY: str = ""
    VOYAGE_API_KEY: str = ""

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # ChromaDB
    CHROMA_PERSIST_PATH: str = "./chroma_data"

    # CORS — comma-separated origins for local dev + Vercel preview
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    # ML model defaults
    CLAUDE_MODEL: str = "claude-sonnet-4-5"
    VOYAGE_MODEL: str = "voyage-3-lite"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
