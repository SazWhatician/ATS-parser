"""Application settings and runtime configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    app_name: str = "ATS Resume Parser & Match Engine"
    app_version: str = "1.0.0"
    author: str = "saswa"
    port: int = 8000
    host: str = "0.0.0.0"
    debug: bool = False

    # Optional LLM API keys - offline heuristic parser runs when these are None/empty
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "google/gemini-2.0-flash-001"
    
    google_api_key: Optional[str] = None
    google_model: str = "gemini-2.0-flash"
    
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    
    llm_timeout: int = 45
    llm_max_retries: int = 2

    # Storage and parsing limits
    max_file_size_bytes: int = 15 * 1024 * 1024  # 15 MB
    allowed_extensions: List[str] = [".pdf", ".docx", ".txt"]
    temp_dir: str = "data/temp"

    @property
    def has_llm_key(self) -> bool:
        """Returns True if any supported LLM API key is present."""
        return bool(
            (self.openrouter_api_key and self.openrouter_api_key.strip()) or
            (self.google_api_key and self.google_api_key.strip()) or
            (self.openai_api_key and self.openai_api_key.strip())
        )

    @property
    def active_engine_mode(self) -> str:
        """Returns 'llm' if an API key is available, else 'heuristic'."""
        return "llm" if self.has_llm_key else "heuristic"


settings = Settings()
