from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Patient Identity Matching System"
    api_key: str = Field(default="demo-key", alias="API_KEY")
    database_url: str = Field(
        default="sqlite:////tmp/patient_matching.db",
        alias="DATABASE_URL",
    )
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    artifacts_dir: Path = Path("artifacts")
    uploads_dir: Path = Path("uploads")
    embedding_dim: int = 384


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    return settings
