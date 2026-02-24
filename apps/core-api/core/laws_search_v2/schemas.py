from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def stable_node_id(citation: str, version_id: str | None, doc_family_id: str | None) -> str:
    base = normalize_ws(citation).lower()
    version = normalize_ws(version_id or doc_family_id or "base").lower()
    return f"{base}|{version}"


def deterministic_uuid(*parts: str) -> uuid.UUID:
    joined = "::".join(parts)
    return uuid.uuid5(uuid.NAMESPACE_URL, joined)


@dataclass(frozen=True)
class RegulatoryDocumentRecord:
    id: Any
    citation: str
    title: str
    jurisdiction: str
    agency: str
    instrument_type: str
    body_text: str
    source_url: str
    content_hash: str
    effective_date: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    version_id: str | None = None
    doc_family_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RegulatoryChunk:
    chunk_id: str
    doc_id: Any
    node_id: str
    citation: str
    chunk_index: int
    heading_path: str | None
    text: str
    span_start: int | None
    span_end: int | None
    chunk_hash: str
    created_at: datetime
    updated_at: datetime
    source_doc_hash: str


@dataclass(frozen=True)
class ObligationCardDraft:
    chunk_id: str
    applies_to: list[str]
    jurisdiction: str
    agency: str
    instrument_type: str
    obligation_type: str
    must_do: str
    conditions: str | None
    artifacts_required: list[str]
    exceptions: str | None
    plain_english_summary: list[str]
    grounding: dict[str, Any]
    review_status: str = "unreviewed"
    confidence: float | None = None
    generated_by: dict[str, Any] = field(default_factory=dict)
    source_doc_hash: str = ""


@dataclass(frozen=True)
class ObligationCardRecord:
    obligation_id: uuid.UUID
    chunk_id: str
    applies_to: list[str]
    jurisdiction: str
    agency: str
    instrument_type: str
    obligation_type: str
    must_do: str
    conditions: str | None
    artifacts_required: list[str]
    exceptions: str | None
    plain_english_summary: list[str]
    grounding: dict[str, Any]
    review_status: str
    confidence: float | None
    generated_by: dict[str, Any]
    source_doc_hash: str
    created_at: datetime


def chunk_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def make_chunk_id(node_id: str, chunk_index: int, content_hash: str) -> str:
    return f"{node_id}:{chunk_index}:{(content_hash or '')[:12]}"


def ensure_uuid(value: Any) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    if value is None:
        raise ValueError("id cannot be None")
    try:
        return uuid.UUID(str(value))
    except Exception:
        # Compatibility path for legacy integer IDs.
        return deterministic_uuid("legacy-doc-id", str(value))


def coerce_doc_id(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
        return stripped
    return value
