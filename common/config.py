from functools import lru_cache
import os
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

    @property
    def is_serverless_runtime(self) -> bool:
        return os.getenv("VERCEL") == "1"

    @property
    def runtime_root(self) -> Path:
        if self.is_serverless_runtime:
            return Path("/tmp/patient_matching")
        return Path(".")

    @property
    def models_dir(self) -> Path:
        return self.artifacts_dir / "models"

    @property
    def generated_data_dir(self) -> Path:
        return self.artifacts_dir / "generated"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    if not settings.artifacts_dir.is_absolute():
        settings.artifacts_dir = settings.runtime_root / settings.artifacts_dir
    if not settings.uploads_dir.is_absolute():
        settings.uploads_dir = settings.runtime_root / settings.uploads_dir

    for path in [settings.runtime_root, settings.artifacts_dir, settings.uploads_dir, settings.models_dir]:
        path.mkdir(parents=True, exist_ok=True)
    return settings
