from __future__ import annotations

from typing import Any

from psycopg2.extras import RealDictCursor

try:
    from laws_search.ingestion import IngestionOrchestrator as LegacyIngestionOrchestrator
except Exception:  # pragma: no cover - optional legacy dependency
    LegacyIngestionOrchestrator = object  # type: ignore[misc,assignment]

from .postprocess.postprocessor import PostProcessor


class IngestionOrchestratorV2(LegacyIngestionOrchestrator):
    """Decorator-style extension over the existing ingestion orchestrator.

    Runs the base ingestion flow and then executes v2 law-KB post-processing.
    """

    def __init__(self, *args: Any, postprocessor: PostProcessor, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.postprocessor = postprocessor

    def run_ingestion(self) -> dict:
        result = super().run_ingestion()

        # TODO: Update fetchers to return changed doc IDs directly.
        # For now we derive candidate docs from DB rows and post-process that set.
        try:
            docs = self._load_documents_for_postprocess(minutes=None)
            post_stats = self.postprocessor.process_documents(docs=docs)
            result["law_kb_postprocess"] = post_stats
        except Exception as exc:
            result["law_kb_postprocess"] = {"error": str(exc)}

        return result

    def _load_documents_for_postprocess(self, minutes: int | None = None) -> list[dict]:
        if minutes is None:
            sql = "SELECT * FROM regulatory_documents"
            params = None
        else:
            sql = (
                "SELECT * FROM regulatory_documents "
                "WHERE updated_at >= NOW() - (%s || ' minutes')::interval"
            )
            params = (str(minutes),)

        rows: list[dict] = []
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                rows = [dict(row) for row in cursor.fetchall()]

        # PostProcessor accepts dict-like docs and derives IDs from rows.
        return rows
