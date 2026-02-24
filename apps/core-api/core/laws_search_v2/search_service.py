from __future__ import annotations

from typing import Any

from .db import LawRepository
from .postprocess.indexers import LawIndexer


class LawSearchService:
    def __init__(self, repository: LawRepository, indexer: LawIndexer | None = None):
        self.repository = repository
        self.indexer = indexer

    def search(
        self,
        query: str,
        jurisdiction: str | None = None,
        agency: str | None = None,
        instrument_type: str | None = None,
        top_k: int = 20,
    ) -> dict[str, Any]:
        if self.indexer is not None:
            rows = self.indexer.search_obligations(
                query=query,
                top_k=top_k,
                jurisdiction=jurisdiction,
                agency=agency,
                instrument_type=instrument_type,
            )
        else:
            rows = self.repository.search_obligations_text(
                query=query,
                top_k=top_k,
                jurisdiction=jurisdiction,
                agency=agency,
                instrument_type=instrument_type,
            )

        results = [
            {
                "obligation_id": row.get("obligation_id"),
                "summary_bullets": row.get("plain_english_summary") or [],
                "must_do": row.get("must_do"),
                "conditions": row.get("conditions"),
                "artifacts_required": row.get("artifacts_required") or [],
                "excerpt": row.get("excerpt") or "",
                "citation": row.get("citation"),
                "title": row.get("title"),
                "jurisdiction": row.get("jurisdiction"),
                "agency": row.get("agency"),
                "source_url": row.get("source_url"),
                "grounding": row.get("grounding") or {},
                "confidence": row.get("confidence"),
                "review_status": row.get("review_status") or "unreviewed",
            }
            for row in rows
        ]
        return {
            "total": len(results),
            "results": results,
        }
