from pathlib import Path
import json
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Comply AI Core Platform"
    app_env: str = "development"
    log_level: str = "INFO"

    core_db_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/core"
    redis_url: str | None = None
    redis_host: str | None = None
    redis_port: int | None = None
    redis_db: int | None = None
    redis_username: str | None = None
    redis_password: str | None = None

    jwt_secret: str = "dev-core-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_exp_minutes: int = 60

    connector_base_url: str = "http://localhost:8100"
    connector_bank_urls: str = "{}"
    connector_api_key: str = "dev-connector-key"
    connector_require_signed: bool = False
    connector_signed_secret: str = "dev-signing-secret"

    llm_provider: str = "mock"
    llm_model_name: str = "mock-llm-v1"
    prompt_version: str = "v1"
    casefile_schema_version: str = "1.0"
    cors_allow_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    celery_task_always_eager: bool = False
    auto_ingest_enabled: bool = True
    auto_ingest_interval_seconds: int = 30
    auto_ingest_batch_size: int = 100
    auto_ingest_overlap_seconds: int = 30

    # Reserved for optional search integration (OpenSearch / Elasticsearch)
    elasticsearch_url: str | None = None
    elasticsearch_username: str | None = None
    elasticsearch_password: str | None = None

    # Optional AWS integration settings
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str | None = None
    s3_bucket: str | None = None

    @property
    def monorepo_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    @property
    def shared_root(self) -> Path:
        return self.monorepo_root / "packages" / "shared"

    @property
    def connector_bank_url_map(self) -> dict[str, str]:
        try:
            data = json.loads(self.connector_bank_urls)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except json.JSONDecodeError:
            pass
        return {}

    @property
    def cors_allow_origin_list(self) -> list[str]:
        raw = (self.cors_allow_origins or "").strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass
        return [item.strip() for item in raw.split(",") if item.strip()]

    @property
    def resolved_redis_url(self) -> str:
        if self.redis_url and self.redis_url.strip():
            return self.redis_url.strip()
        host = (self.redis_host or "").strip()
        if not host:
            return "redis://localhost:6379/0"
        port = self.redis_port or 6379
        db = self.redis_db if self.redis_db is not None else 0
        username = (self.redis_username or "").strip()
        password = self.redis_password or ""
        if username:
            return f"rediss://{quote_plus(username)}:{quote_plus(password)}@{host}:{port}/{db}"
        if password:
            return f"rediss://:{quote_plus(password)}@{host}:{port}/{db}"
        return f"redis://{host}:{port}/{db}"


settings = Settings()
