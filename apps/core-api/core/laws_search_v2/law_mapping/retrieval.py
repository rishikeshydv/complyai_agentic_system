from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ..db import LawRepository
from ..postprocess.indexers import LawIndexer
from .models import Event


@dataclass(frozen=True)
class RetrievalCandidate:
    obligation_id: str
    must_do: str
    conditions: str | None
    artifacts_required: list[str]
    summary_bullets: list[str]
    grounding: dict[str, Any]
    chunk_id: str
    citation: str
    title: str
    jurisdiction: str
    agency: str
    source_url: str | None
    excerpt: str
    confidence: float | None
    review_status: str


class ObligationRetriever(Protocol):
    def retrieve(self, event: Event, top_k: int = 12) -> list[RetrievalCandidate]: ...


class IndexObligationRetriever:
    def __init__(self, indexer: LawIndexer):
        self.indexer = indexer

    def retrieve(self, event: Event, top_k: int = 12) -> list[RetrievalCandidate]:
        query = build_fallback_query(event)
        raw = self.indexer.search_obligations(
            query=query,
            top_k=top_k,
        )
        return [to_candidate(row) for row in raw]


class RepositoryObligationRetriever:
    def __init__(self, repository: LawRepository):
        self.repository = repository

    def retrieve(self, event: Event, top_k: int = 12) -> list[RetrievalCandidate]:
        query = build_fallback_query(event)
        raw = self.repository.search_obligations_text(query=query, top_k=top_k)
        return [to_candidate(row) for row in raw]


def build_fallback_query(event: Event) -> str:
    condition_parts = []
    for idx, cond in enumerate(event.conditions_triggered):
        condition_parts.append(
            f"[{idx}] {cond.field} {cond.operator} threshold={cond.threshold} actual={cond.actual} window={cond.window_days}"
        )
    return " ".join([event.rule_description, *condition_parts]).strip()


def to_candidate(row: dict[str, Any]) -> RetrievalCandidate:
    return RetrievalCandidate(
        obligation_id=str(row.get("obligation_id")),
        must_do=row.get("must_do") or "",
        conditions=row.get("conditions"),
        artifacts_required=list(row.get("artifacts_required") or []),
        summary_bullets=list(row.get("plain_english_summary") or []),
        grounding=dict(row.get("grounding") or {}),
        chunk_id=row.get("chunk_id") or "",
        citation=row.get("citation") or "",
        title=row.get("title") or "",
        jurisdiction=row.get("jurisdiction") or "",
        agency=row.get("agency") or "",
        source_url=row.get("source_url"),
        excerpt=row.get("excerpt") or "",
        confidence=row.get("confidence"),
        review_status=row.get("review_status") or "unreviewed",
    )
