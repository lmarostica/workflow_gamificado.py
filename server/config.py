from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ORCH_", env_file=".env", extra="ignore"
    )

    client_api_key: str = "dev-client-key"
    worker_api_key: str = "dev-worker-key"
    db_path: str = "orquestrador.db"
    orphan_timeout_seconds: int = 120
    reaper_interval_seconds: int = 60
    default_job_timeout_seconds: int = 3600
    log_tail_max_bytes: int = 64 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
