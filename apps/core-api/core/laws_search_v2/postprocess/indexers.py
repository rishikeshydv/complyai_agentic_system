from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

try:
    from elasticsearch import Elasticsearch, helpers
except Exception:  # pragma: no cover - optional dependency for local-only tests
    Elasticsearch = Any  # type: ignore

    class _MissingHelpers:
        @staticmethod
        def bulk(*args, **kwargs):
            raise RuntimeError("elasticsearch package is not installed")

    helpers = _MissingHelpers()

from ..config import settings
from ..schemas import ObligationCardRecord, RegulatoryChunk, RegulatoryDocumentRecord


class LawIndexer(Protocol):
    def ensure_indices(self) -> None: ...

    def index_chunks(
        self,
        chunks: list[RegulatoryChunk],
        docs_by_id: dict,
    ) -> tuple[int, int]: ...

    def index_obligations(
        self,
        obligations: list[ObligationCardRecord],
        chunks_by_id: dict[str, RegulatoryChunk],
        docs_by_id: dict,
    ) -> tuple[int, int]: ...

    def search_obligations(
        self,
        query: str,
        top_k: int,
        jurisdiction: str | None = None,
        agency: str | None = None,
        instrument_type: str | None = None,
    ) -> list[dict[str, Any]]: ...


class ElasticsearchLawIndexer:
    def __init__(
        self,
        es_client: Elasticsearch | None = None,
        chunks_index: str | None = None,
        obligations_index: str | None = None,
    ):
        self.es = es_client or Elasticsearch(settings.es_url, api_key=settings.es_api_key)
        self.chunks_index = chunks_index or settings.es_chunks_index
        self.obligations_index = obligations_index or settings.es_obligations_index

    def ensure_indices(self) -> None:
        self._ensure_chunks_index()
        self._ensure_obligations_index()

    def _ensure_chunks_index(self) -> None:
        if self.es.indices.exists(index=self.chunks_index):
            return
        # TODO: add dense_vector embeddings when retrieval stack is upgraded.
        body = {
            "mappings": {
                "properties": {
                    "chunk_id": {"type": "keyword"},
                    "doc_id": {"type": "keyword"},
                    "node_id": {"type": "keyword"},
                    "citation": {"type": "keyword"},
                    "title": {"type": "text"},
                    "jurisdiction": {"type": "keyword"},
                    "agency": {"type": "keyword"},
                    "instrument_type": {"type": "keyword"},
                    "heading_path": {"type": "text"},
                    "text": {"type": "text"},
                    "source_url": {"type": "keyword"},
                    "content_hash": {"type": "keyword"},
                }
            }
        }
        self.es.indices.create(index=self.chunks_index, body=body)

    def _ensure_obligations_index(self) -> None:
        if self.es.indices.exists(index=self.obligations_index):
            return
        # TODO: add dense_vector embeddings for semantic retrieval.
        body = {
            "mappings": {
                "properties": {
                    "obligation_id": {"type": "keyword"},
                    "chunk_id": {"type": "keyword"},
                    "citation": {"type": "keyword"},
                    "title": {"type": "text"},
                    "jurisdiction": {"type": "keyword"},
                    "agency": {"type": "keyword"},
                    "instrument_type": {"type": "keyword"},
                    "obligation_type": {"type": "keyword"},
                    "must_do": {"type": "text"},
                    "conditions": {"type": "text"},
                    "artifacts_required": {"type": "keyword"},
                    "plain_english_summary": {"type": "text"},
                    "excerpt": {"type": "text"},
                    "source_url": {"type": "keyword"},
                    "grounding": {"type": "object", "enabled": True},
                    "confidence": {"type": "float"},
                    "review_status": {"type": "keyword"},
                }
            }
        }
        self.es.indices.create(index=self.obligations_index, body=body)

    def index_chunks(
        self,
        chunks: list[RegulatoryChunk],
        docs_by_id: dict,
    ) -> tuple[int, int]:
        if not chunks:
            return (0, 0)

        actions = []
        for chunk in chunks:
            doc = docs_by_id.get(chunk.doc_id)
            if not doc:
                continue
            actions.append(
                {
                    "_index": self.chunks_index,
                    "_id": chunk.chunk_id,
                    "_source": {
                        "chunk_id": chunk.chunk_id,
                        "doc_id": str(chunk.doc_id),
                        "node_id": chunk.node_id,
                        "citation": chunk.citation,
                        "title": doc.title,
                        "jurisdiction": doc.jurisdiction,
                        "agency": doc.agency,
                        "instrument_type": doc.instrument_type,
                        "heading_path": chunk.heading_path,
                        "text": chunk.text,
                        "source_url": doc.source_url,
                        "content_hash": chunk.source_doc_hash,
                    },
                }
            )

        success, errors = helpers.bulk(
            self.es,
            actions,
            raise_on_error=False,
            raise_on_exception=False,
            chunk_size=100,
            request_timeout=180,
            max_retries=3,
            initial_backoff=2,
            max_backoff=30,
        )
        return success, len(errors)

    def index_obligations(
        self,
        obligations: list[ObligationCardRecord],
        chunks_by_id: dict[str, RegulatoryChunk],
        docs_by_id: dict,
    ) -> tuple[int, int]:
        if not obligations:
            return (0, 0)

        actions = []
        for obligation in obligations:
            chunk = chunks_by_id.get(obligation.chunk_id)
            if not chunk:
                continue
            doc = docs_by_id.get(chunk.doc_id)
            actions.append(
                {
                    "_index": self.obligations_index,
                    "_id": str(obligation.obligation_id),
                    "_source": {
                        "obligation_id": str(obligation.obligation_id),
                        "chunk_id": obligation.chunk_id,
                        "citation": chunk.citation,
                        "title": doc.title if doc else "",
                        "jurisdiction": obligation.jurisdiction,
                        "agency": obligation.agency,
                        "instrument_type": obligation.instrument_type,
                        "obligation_type": obligation.obligation_type,
                        "must_do": obligation.must_do,
                        "conditions": obligation.conditions,
                        "artifacts_required": obligation.artifacts_required,
                        "plain_english_summary": obligation.plain_english_summary,
                        "excerpt": chunk.text,
                        "source_url": doc.source_url if doc else None,
                        "grounding": obligation.grounding,
                        "confidence": obligation.confidence,
                        "review_status": obligation.review_status,
                    },
                }
            )

        success, errors = helpers.bulk(
            self.es,
            actions,
            raise_on_error=False,
            raise_on_exception=False,
            chunk_size=100,
            request_timeout=180,
            max_retries=3,
            initial_backoff=2,
            max_backoff=30,
        )
        return success, len(errors)

    def search_obligations(
        self,
        query: str,
        top_k: int,
        jurisdiction: str | None = None,
        agency: str | None = None,
        instrument_type: str | None = None,
    ) -> list[dict[str, Any]]:
        must_filters: list[dict[str, Any]] = []
        if jurisdiction:
            must_filters.append({"term": {"jurisdiction": jurisdiction}})
        if agency:
            must_filters.append({"term": {"agency": agency}})
        if instrument_type:
            must_filters.append({"term": {"instrument_type": instrument_type}})

        body = {
            "size": top_k,
            "query": {
                "bool": {
                    "must": {
                        "multi_match": {
                            "query": query,
                            "fields": [
                                "must_do^3",
                                "conditions^2",
                                "plain_english_summary^2",
                                "excerpt",
                            ],
                            "operator": "or",
                        }
                    },
                    "filter": must_filters,
                }
            },
            "highlight": {
                "fields": {
                    "excerpt": {"fragment_size": 220, "number_of_fragments": 1},
                    "must_do": {"fragment_size": 140, "number_of_fragments": 1},
                }
            },
        }
        resp = self.es.search(index=self.obligations_index, body=body)
        hits = resp.get("hits", {}).get("hits", [])

        rows: list[dict[str, Any]] = []
        for hit in hits:
            source = hit.get("_source", {})
            highlight = hit.get("highlight", {})
            excerpt = None
            if highlight.get("excerpt"):
                excerpt = highlight["excerpt"][0]
            elif highlight.get("must_do"):
                excerpt = highlight["must_do"][0]
            else:
                excerpt = source.get("excerpt", "")[:220]
            rows.append(
                {
                    **source,
                    "excerpt": excerpt,
                    "_score": hit.get("_score"),
                }
            )
        return rows


@dataclass
class InMemoryLawIndexer:
    chunk_docs: dict[str, dict[str, Any]] = None
    obligation_docs: dict[str, dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.chunk_docs is None:
            self.chunk_docs = {}
        if self.obligation_docs is None:
            self.obligation_docs = {}

    def ensure_indices(self) -> None:
        return

    def index_chunks(
        self,
        chunks: list[RegulatoryChunk],
        docs_by_id: dict,
    ) -> tuple[int, int]:
        count = 0
        for chunk in chunks:
            doc: RegulatoryDocumentRecord | None = docs_by_id.get(chunk.doc_id)
            self.chunk_docs[chunk.chunk_id] = {
                "chunk_id": chunk.chunk_id,
                "citation": chunk.citation,
                "title": doc.title if doc else "",
                "jurisdiction": doc.jurisdiction if doc else "",
                "agency": doc.agency if doc else "",
                "instrument_type": doc.instrument_type if doc else "",
                "text": chunk.text,
                "heading_path": chunk.heading_path,
                "source_url": doc.source_url if doc else None,
            }
            count += 1
        return count, 0

    def index_obligations(
        self,
        obligations: list[ObligationCardRecord],
        chunks_by_id: dict[str, RegulatoryChunk],
        docs_by_id: dict,
    ) -> tuple[int, int]:
        count = 0
        for obligation in obligations:
            chunk = chunks_by_id.get(obligation.chunk_id)
            if not chunk:
                continue
            doc: RegulatoryDocumentRecord | None = docs_by_id.get(chunk.doc_id)
            self.obligation_docs[str(obligation.obligation_id)] = {
                "obligation_id": str(obligation.obligation_id),
                "chunk_id": obligation.chunk_id,
                "citation": chunk.citation,
                "title": doc.title if doc else "",
                "jurisdiction": obligation.jurisdiction,
                "agency": obligation.agency,
                "instrument_type": obligation.instrument_type,
                "obligation_type": obligation.obligation_type,
                "must_do": obligation.must_do,
                "conditions": obligation.conditions,
                "artifacts_required": list(obligation.artifacts_required),
                "plain_english_summary": list(obligation.plain_english_summary),
                "excerpt": chunk.text,
                "source_url": doc.source_url if doc else None,
                "grounding": dict(obligation.grounding),
                "confidence": obligation.confidence,
                "review_status": obligation.review_status,
            }
            count += 1
        return count, 0

    def search_obligations(
        self,
        query: str,
        top_k: int,
        jurisdiction: str | None = None,
        agency: str | None = None,
        instrument_type: str | None = None,
    ) -> list[dict[str, Any]]:
        q = query.lower().strip()
        tokens = [token for token in q.split() if len(token) > 2]
        scored: list[tuple[int, dict[str, Any]]] = []
        for row in self.obligation_docs.values():
            if jurisdiction and row.get("jurisdiction") != jurisdiction:
                continue
            if agency and row.get("agency") != agency:
                continue
            if instrument_type and row.get("instrument_type") != instrument_type:
                continue

            haystack = " ".join(
                [
                    row.get("must_do") or "",
                    row.get("conditions") or "",
                    " ".join(row.get("plain_english_summary") or []),
                    row.get("excerpt") or "",
                ]
            ).lower()
            if tokens:
                score = sum(haystack.count(token) for token in tokens)
            else:
                score = haystack.count(q)
            if score > 0:
                scored.append((score, row))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {**row, "excerpt": (row.get("excerpt") or "")[:220], "_score": score}
            for score, row in scored[:top_k]
        ]
