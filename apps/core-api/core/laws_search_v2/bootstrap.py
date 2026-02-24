from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import Column, Integer, Table, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy import create_engine

from core.config import settings as core_settings

from .config import settings
from .db import SQLLawRepository
from .models_sqlalchemy import Base as LawsV2Base
from .postprocess.postprocessor import PostProcessor
from .runtime import NoopLawIndexer
from .seeds.seed_law_mapping import main as seed_law_mapping_main


def _laws_file() -> Path:
    return core_settings.shared_root / "laws" / "citations.yaml"


def _normalize_jurisdiction(value: str) -> str:
    raw = (value or "").strip().upper()
    if raw in {"US", "USA", "FEDERAL"}:
        return "federal"
    if raw in {"NJ", "NEW JERSEY"}:
        return "nj"
    return (value or "federal").strip().lower()


def _normalize_agency(alert_type: str) -> str:
    return "ofac" if (alert_type or "").strip().upper() == "SANCTIONS" else "fincen"


def _normalize_instrument(alert_type: str) -> str:
    upper = (alert_type or "").strip().upper()
    if upper == "SANCTIONS":
        return "sanctions"
    return "aml"


def _mapping_seed_hint(alert_type: str) -> str:
    upper = (alert_type or "").strip().upper()
    if upper == "SANCTIONS":
        return "OFAC sanctions screen obligations and blocked-party handling."
    return "Suspicious activity report filing obligations and CTR monitoring expectations."


def ensure_regulatory_documents_table(engine: Engine) -> None:
    inspector = inspect(engine)
    if inspector.has_table("regulatory_documents"):
        return
    create_sql = """
    CREATE TABLE regulatory_documents (
        id SERIAL PRIMARY KEY,
        citation TEXT NOT NULL,
        title TEXT NOT NULL,
        jurisdiction TEXT NOT NULL,
        agency TEXT NOT NULL,
        instrument_type TEXT NOT NULL,
        body_text TEXT NOT NULL,
        source_url TEXT NOT NULL DEFAULT '',
        content_hash TEXT NOT NULL,
        effective_date DATE NULL,
        effective_from DATE NULL,
        effective_to DATE NULL,
        version_id TEXT NULL,
        doc_family_id TEXT NULL,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    with engine.begin() as conn:
        conn.execute(text(create_sql))


def ensure_laws_v2_tables(engine: Engine) -> None:
    Table(
        "regulatory_documents",
        LawsV2Base.metadata,
        Column("id", Integer, primary_key=True),
        extend_existing=True,
    )
    LawsV2Base.metadata.create_all(bind=engine)


def seed_regulatory_documents(engine: Engine) -> None:
    with _laws_file().open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    citations: list[dict[str, Any]] = data.get("citations", [])
    if not citations:
        return

    select_stmt = text("SELECT id, content_hash FROM regulatory_documents WHERE citation = :citation")
    insert_stmt = text(
        """
        INSERT INTO regulatory_documents (
            citation, title, jurisdiction, agency, instrument_type, body_text, source_url,
            content_hash, metadata, updated_at
        ) VALUES (
            :citation, :title, :jurisdiction, :agency, :instrument_type, :body_text, :source_url,
            :content_hash, CAST(:metadata AS jsonb), NOW()
        )
        """
    )
    update_stmt = text(
        """
        UPDATE regulatory_documents
        SET title = :title,
            jurisdiction = :jurisdiction,
            agency = :agency,
            instrument_type = :instrument_type,
            body_text = :body_text,
            source_url = :source_url,
            content_hash = :content_hash,
            metadata = CAST(:metadata AS jsonb),
            updated_at = NOW()
        WHERE id = :id
        """
    )
    delete_stale_obligations_stmt = text(
        """
        DELETE FROM obligation_cards o
        USING regulatory_chunks c
        WHERE o.chunk_id = c.chunk_id
          AND c.citation = :citation
          AND c.source_doc_hash <> :content_hash
        """
    )
    delete_stale_chunks_stmt = text(
        """
        DELETE FROM regulatory_chunks
        WHERE citation = :citation
          AND source_doc_hash <> :content_hash
        """
    )

    with engine.begin() as conn:
        for row in citations:
            citation_id = str(row.get("citation_id", "")).strip()
            if not citation_id:
                continue
            alert_type = str(row.get("alert_type", "AML"))
            title = str(row.get("title", citation_id))
            snippet = str(row.get("text_snippet", "")).strip()
            body_text = (
                f"Alert type: {alert_type}. Citation: {citation_id}. Title: {title}. "
                f"{snippet if snippet else 'NOT PROVIDED'} "
                f"{_mapping_seed_hint(alert_type)}"
            )
            content_hash = hashlib.sha256(body_text.encode("utf-8")).hexdigest()
            payload = {
                "citation": citation_id,
                "title": title,
                "jurisdiction": _normalize_jurisdiction(str(row.get("jurisdiction", "US"))),
                "agency": _normalize_agency(alert_type),
                "instrument_type": _normalize_instrument(alert_type),
                "body_text": body_text,
                "source_url": str(row.get("source_url", "") or ""),
                "content_hash": content_hash,
                "metadata": json.dumps(
                    {
                        "seed_source": "packages/shared/laws/citations.yaml",
                        "alert_type": alert_type,
                    }
                ),
            }

            existing = conn.execute(select_stmt, {"citation": citation_id}).fetchone()
            if existing is None:
                conn.execute(insert_stmt, payload)
            elif str(existing.content_hash) != content_hash:
                conn.execute(update_stmt, {**payload, "id": int(existing.id)})

            conn.execute(
                delete_stale_obligations_stmt,
                {"citation": citation_id, "content_hash": content_hash},
            )
            conn.execute(
                delete_stale_chunks_stmt,
                {"citation": citation_id, "content_hash": content_hash},
            )


def backfill_law_kb(engine: Engine) -> None:
    backfill_limit = max(0, int(settings.backfill_limit))
    repo = SQLLawRepository()
    postprocessor = PostProcessor(repository=repo, indexer=NoopLawIndexer())
    sql = """
        SELECT id, citation, title, jurisdiction, agency, instrument_type,
               effective_date, effective_from, effective_to,
               body_text, source_url, content_hash, version_id, doc_family_id, metadata
        FROM regulatory_documents
        ORDER BY id ASC
    """
    params: dict[str, Any] = {}
    if backfill_limit > 0:
        sql += " LIMIT :limit"
        params["limit"] = backfill_limit
    with engine.begin() as conn:
        rows = conn.execute(text(sql), params).fetchall()
    docs = [dict(row._mapping) for row in rows]
    if docs:
        postprocessor.process_documents(docs=docs)


def bootstrap_laws_v2(engine: Engine | None = None) -> None:
    owns_engine = engine is None
    db_engine = engine or create_engine(settings.database_url, future=True, pool_pre_ping=True)
    try:
        if not str(db_engine.url).startswith("postgresql"):
            return
        ensure_regulatory_documents_table(db_engine)
        ensure_laws_v2_tables(db_engine)
        with db_engine.begin() as conn:
            existing_doc_count = int(conn.execute(text("SELECT COUNT(*) FROM regulatory_documents")).scalar() or 0)

        if existing_doc_count == 0 and settings.curated_seed_if_empty:
            seed_regulatory_documents(db_engine)
            with db_engine.begin() as conn:
                existing_doc_count = int(conn.execute(text("SELECT COUNT(*) FROM regulatory_documents")).scalar() or 0)

        if existing_doc_count > 0 and settings.enable_backfill:
            backfill_law_kb(db_engine)

        if settings.enable_mapping_seed:
            seed_law_mapping_main()
    finally:
        if owns_engine:
            db_engine.dispose()
