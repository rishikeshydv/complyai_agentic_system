from __future__ import annotations

import os
from urllib.parse import quote_plus
from dataclasses import dataclass


def _build_aurora_url() -> str | None:
    endpoint = os.getenv("AURORA_ENDPOINT", "").strip()
    user = os.getenv("AURORA_DB_USER", "").strip()
    password = os.getenv("AURORA_DB_PASSWORD", "").strip()
    db_name = os.getenv("AURORA_DB_NAME", "").strip()
    port = os.getenv("AURORA_PORT", "5432").strip() or "5432"
    if not (endpoint and user and password and db_name):
        return None
    return (
        "postgresql+psycopg2://"
        f"{quote_plus(user)}:{quote_plus(password)}@{endpoint}:{port}/{quote_plus(db_name)}"
        "?sslmode=require"
    )


@dataclass(frozen=True)
class Settings:
    database_url: str = (
        os.getenv("LAWS_V2_DATABASE_URL")
        or _build_aurora_url()
        or os.getenv("CORE_DB_URL")
        or "postgresql+psycopg2://postgres:postgres@localhost:5432/comply_ai"
    )
    es_url: str = (
        os.getenv("LAWS_V2_ES_URL")
        or os.getenv("ES_ENDPOINT")
        or os.getenv("ELASTICSEARCH_URL")
        or "http://localhost:9200"
    )
    es_api_key: str | None = os.getenv("LAWS_V2_ES_API_KEY") or os.getenv("ES_API_KEY")
    es_chunks_index: str = os.getenv("LAWS_V2_ES_CHUNKS_INDEX", "reg_chunks")
    es_obligations_index: str = os.getenv("LAWS_V2_ES_OBLIGATIONS_INDEX", "reg_obligations")
    use_es: bool = str(os.getenv("LAWS_V2_USE_ES", "false")).strip().lower() in {"1", "true", "yes", "on"}
    enable_llm: bool = str(os.getenv("LAWS_V2_ENABLE_LLM", "false")).strip().lower() in {"1", "true", "yes", "on"}
    curated_seed_if_empty: bool = str(os.getenv("LAWS_V2_CURATED_SEED_IF_EMPTY", "false")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    enable_backfill: bool = str(os.getenv("LAWS_V2_ENABLE_BACKFILL", "false")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    backfill_limit: int = int(os.getenv("LAWS_V2_BACKFILL_LIMIT", "0"))
    enable_mapping_seed: bool = str(os.getenv("LAWS_V2_ENABLE_MAPPING_SEED", "false")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    chunk_min_chars: int = int(os.getenv("LAWS_V2_CHUNK_MIN_CHARS", "500"))
    chunk_max_chars: int = int(os.getenv("LAWS_V2_CHUNK_MAX_CHARS", "1500"))
    obligation_generator_version: str = os.getenv(
        "LAWS_V2_OBLIGATION_GENERATOR_VERSION",
        "mock-obligation-extractor-v1",
    )


settings = Settings()
