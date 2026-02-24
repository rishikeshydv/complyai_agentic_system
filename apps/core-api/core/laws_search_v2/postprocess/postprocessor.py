from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Sequence

from ..db import LawRepository
from ..schemas import RegulatoryDocumentRecord, coerce_doc_id, deterministic_uuid
from .chunker import DeterministicChunker
from .indexers import LawIndexer
from .obligation_extractor import ExtractionContext, GroundingValidator, MockLLMExtractor, ObligationExtractor


@dataclass
class PostprocessStats:
    processed_documents: int = 0
    chunks_upserted: int = 0
    obligations_upserted: int = 0
    chunk_indexed_success: int = 0
    chunk_indexed_failed: int = 0
    obligation_indexed_success: int = 0
    obligation_indexed_failed: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "processed_documents": self.processed_documents,
            "chunks_upserted": self.chunks_upserted,
            "obligations_upserted": self.obligations_upserted,
            "chunk_indexed_success": self.chunk_indexed_success,
            "chunk_indexed_failed": self.chunk_indexed_failed,
            "obligation_indexed_success": self.obligation_indexed_success,
            "obligation_indexed_failed": self.obligation_indexed_failed,
        }


class PostProcessor:
    def __init__(
        self,
        repository: LawRepository,
        indexer: LawIndexer,
        chunker: DeterministicChunker | None = None,
        extractor: ObligationExtractor | None = None,
    ):
        self.repository = repository
        self.indexer = indexer
        self.chunker = chunker or DeterministicChunker()
        self.extractor = extractor or MockLLMExtractor()

    def process_documents(
        self,
        doc_ids: Sequence[Any] | None = None,
        docs: Sequence[Any] | None = None,
    ) -> dict[str, int]:
        documents = self._resolve_documents(doc_ids=doc_ids, docs=docs)
        stats = PostprocessStats(processed_documents=len(documents))

        if not documents:
            return stats.to_dict()

        self.indexer.ensure_indices()

        docs_by_id = {doc.id: doc for doc in documents}
        all_changed_chunks = []
        all_new_obligations = []

        for doc in documents:
            chunks = self.chunker.chunk_document(doc)
            changed_chunks = self.repository.upsert_chunks(chunks)
            stats.chunks_upserted += len(changed_chunks)
            all_changed_chunks.extend(changed_chunks)

            for chunk in chunks:
                already_extracted = self.repository.has_obligations_for_chunk_version(
                    chunk_id=chunk.chunk_id,
                    source_doc_hash=doc.content_hash,
                    generator_version=self.extractor.generator_version,
                )
                if already_extracted:
                    continue

                context = ExtractionContext(
                    jurisdiction=doc.jurisdiction,
                    agency=doc.agency,
                    instrument_type=doc.instrument_type,
                )
                drafts = self.extractor.extract_obligations(chunk, context)

                valid_drafts = [
                    draft
                    for draft in drafts
                    if GroundingValidator.is_valid(chunk.text, draft.grounding, chunk.chunk_id)
                ]
                if not valid_drafts:
                    continue

                inserted = self.repository.upsert_obligations(
                    drafts=valid_drafts,
                    generator_version=self.extractor.generator_version,
                )
                stats.obligations_upserted += len(inserted)
                all_new_obligations.extend(inserted)

        chunks_by_id = {chunk.chunk_id: chunk for chunk in all_changed_chunks}
        chunk_ok, chunk_failed = self.indexer.index_chunks(all_changed_chunks, docs_by_id=docs_by_id)
        ob_ok, ob_failed = self.indexer.index_obligations(
            all_new_obligations,
            chunks_by_id=chunks_by_id,
            docs_by_id=docs_by_id,
        )

        stats.chunk_indexed_success = chunk_ok
        stats.chunk_indexed_failed = chunk_failed
        stats.obligation_indexed_success = ob_ok
        stats.obligation_indexed_failed = ob_failed

        return stats.to_dict()

    def _resolve_documents(
        self,
        doc_ids: Sequence[Any] | None,
        docs: Sequence[Any] | None,
    ) -> list[RegulatoryDocumentRecord]:
        if docs:
            return [self._coerce_document(doc) for doc in docs]
        if doc_ids:
            return self.repository.get_documents_by_ids(doc_ids)
        return []

    def _coerce_document(self, doc: Any) -> RegulatoryDocumentRecord:
        if isinstance(doc, RegulatoryDocumentRecord):
            return doc

        def _iso(value: Any) -> Any:
            return value.isoformat() if hasattr(value, "isoformat") else value

        if isinstance(doc, dict):
            get = doc.get
            raw_id = get("id") or get("doc_id")
            citation = get("citation", "")
            title = get("title", "")
            jurisdiction = get("jurisdiction", "")
            agency = get("agency", "")
            instrument_type = get("instrument_type", "")
            body_text = get("body_text", "") or ""
            source_url = get("source_url", "") or ""
            content_hash = get("content_hash", "") or ""
            effective_date = _iso(get("effective_date"))
            effective_from = _iso(get("effective_from"))
            effective_to = _iso(get("effective_to"))
            version_id = get("version_id")
            doc_family_id = get("doc_family_id")
            metadata = get("metadata") or {}
        else:
            raw_id = getattr(doc, "id", None) or getattr(doc, "doc_id", None)
            citation = getattr(doc, "citation", "")
            title = getattr(doc, "title", "")
            jurisdiction = getattr(getattr(doc, "jurisdiction", None), "value", getattr(doc, "jurisdiction", ""))
            agency = getattr(getattr(doc, "agency", None), "value", getattr(doc, "agency", ""))
            instrument_type = getattr(
                getattr(doc, "instrument_type", None),
                "value",
                getattr(doc, "instrument_type", ""),
            )
            body_text = getattr(doc, "body_text", "") or ""
            source_url = getattr(doc, "source_url", "") or ""
            content_hash = getattr(doc, "content_hash", "") or ""
            effective_date = _iso(getattr(doc, "effective_date", None))
            effective_from = _iso(getattr(doc, "effective_from", None))
            effective_to = _iso(getattr(doc, "effective_to", None))
            version_id = getattr(doc, "version_id", None)
            doc_family_id = getattr(doc, "doc_family_id", None)
            metadata = getattr(doc, "metadata", None) or {}

        if raw_id is None:
            raw_id = deterministic_uuid(
                "legacy-regulatory-document",
                citation,
                content_hash,
            )
        doc_id = coerce_doc_id(raw_id)

        return RegulatoryDocumentRecord(
            id=doc_id,
            citation=citation,
            title=title,
            jurisdiction=jurisdiction,
            agency=agency,
            instrument_type=instrument_type,
            body_text=body_text,
            source_url=source_url,
            content_hash=content_hash,
            effective_date=effective_date,
            effective_from=effective_from,
            effective_to=effective_to,
            version_id=version_id,
            doc_family_id=doc_family_id,
            metadata=metadata,
        )
