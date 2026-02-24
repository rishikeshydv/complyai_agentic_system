from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Comply AI Connector"
    app_env: str = "development"
    log_level: str = "INFO"

    connector_db_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5434/connector"
    connector_api_key: str = "dev-connector-key"

    require_signed_requests: bool = False
    signed_request_secret: str = "dev-signing-secret"
    core_alert_callback_url: Optional[str] = None

    field_allowlist_path: str = "apps/connector/connector/allowlist.yaml"

    # Reserved for optional connector-side cache/search integration
    redis_url: Optional[str] = None
    elasticsearch_url: Optional[str] = None
    elasticsearch_username: Optional[str] = None
    elasticsearch_password: Optional[str] = None

    @property
    def resolved_allowlist_path(self) -> Path:
        root = Path(__file__).resolve().parents[3]
        candidate = root / self.field_allowlist_path
        return candidate


settings = Settings()
