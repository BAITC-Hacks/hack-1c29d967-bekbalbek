from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://agent:agent@localhost:5433/agent_workspace"
    openai_api_key: str | None = None
    openai_model: str = "qwen3.5:4b"
    openai_base_url: str | None = "http://localhost:11434/v1"
    stt_device: Literal["auto", "cuda", "cpu"] = "auto"
    models_dir: Path = Path(__file__).resolve().parents[1] / "models"
    media_dir: Path = Path(__file__).resolve().parents[1] / "media"
    samples_dir: Path = Path(__file__).resolve().parents[1] / "samples"
    diarize_threshold: float = Field(default=0.7, gt=0, lt=2)

    agent_max_turns: int = Field(default=12, ge=1, le=100)
    agent_run_timeout_seconds: float = Field(default=300, gt=0)
    tool_timeout_seconds: float = Field(default=15, gt=0)
    tool_max_retries: int = Field(default=2, ge=0, le=10)
    tool_result_max_chars: int = Field(default=6000, ge=200)
    agent_max_revisions: int = Field(default=1, ge=0, le=3)

    app_env: str = "dev"
    app_version: str = "0.1.0"
    cors_origins: str = "http://localhost:5173"
    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def api_key_configured(self) -> bool:
        return bool(self.openai_api_key and not self.openai_api_key.startswith("sk-..."))


@lru_cache
def get_settings() -> Settings:
    return Settings()
