from __future__ import annotations

import json
import uuid
from typing import Any, Protocol, Sequence

from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.engine import Engine

from .config import settings
from .law_mapping.models import (
    ControlObjective,
    ControlToObligationMap,
    ProposedRuleMap,
    RuleToTypologyMap,
    Typology,
)
from .schemas import (
    ObligationCardDraft,
    ObligationCardRecord,
    RegulatoryChunk,
    RegulatoryDocumentRecord,
    coerce_doc_id,
    deterministic_uuid,
    ensure_uuid,
    utcnow,
)


class LawRepository(Protocol):
    def get_documents_by_ids(self, doc_ids: Sequence[Any]) -> list[RegulatoryDocumentRecord]: ...

    def upsert_chunks(self, chunks: Sequence[RegulatoryChunk]) -> list[RegulatoryChunk]: ...

    def has_obligations_for_chunk_version(
        self,
        chunk_id: str,
        source_doc_hash: str,
        generator_version: str,
    ) -> bool: ...

    def upsert_obligations(
        self,
        drafts: Sequence[ObligationCardDraft],
        generator_version: str,
    ) -> list[ObligationCardRecord]: ...

    def get_chunk(self, chunk_id: str) -> RegulatoryChunk | None: ...

    def get_document(self, doc_id: Any) -> RegulatoryDocumentRecord | None: ...

    def get_obligations_by_ids(self, obligation_ids: Sequence[uuid.UUID]) -> list[ObligationCardRecord]: ...

    def get_obligations_with_context(
        self,
        obligation_ids: Sequence[uuid.UUID],
    ) -> list[dict[str, Any]]: ...

    def get_latest_rule_map(self, bank_id: str, rule_triggered: str) -> RuleToTypologyMap | None: ...

    def get_typology(self, typology_id: str) -> Typology | None: ...

    def get_control_objectives(self, control_ids: Sequence[str]) -> list[ControlObjective]: ...

    def get_control_to_obligation_maps(
        self,
        control_ids: Sequence[str],
        jurisdiction_context: str | None = None,
    ) -> list[ControlToObligationMap]: ...

    def save_proposed_rule_map(self, proposal: ProposedRuleMap) -> None: ...

    def search_obligations_text(
        self,
        query: str,
        top_k: int,
        jurisdiction: str | None = None,
        agency: str | None = None,
        instrument_type: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def upsert_control_objective(self, control: ControlObjective) -> None: ...

    def upsert_typology(self, typology: Typology) -> None: ...

    def upsert_rule_map(self, mapping: RuleToTypologyMap) -> None: ...

    def upsert_control_to_obligation_map(self, mapping: ControlToObligationMap) -> None: ...


class SQLLawRepository:
    """Postgres-backed repository for law KB and mapping entities."""

    def __init__(self, database_url: str | None = None):
        self.engine: Engine = create_engine(database_url or settings.database_url, future=True)

    def _row_to_document(self, row: Any) -> RegulatoryDocumentRecord:
        return RegulatoryDocumentRecord(
            id=coerce_doc_id(row.id),
            citation=row.citation,
            title=row.title,
            jurisdiction=row.jurisdiction,
            agency=row.agency,
            instrument_type=row.instrument_type,
            body_text=row.body_text or "",
            source_url=row.source_url or "",
            content_hash=row.content_hash or "",
            effective_date=row.effective_date.isoformat() if row.effective_date else None,
            effective_from=row.effective_from.isoformat() if getattr(row, "effective_from", None) else None,
            effective_to=row.effective_to.isoformat() if getattr(row, "effective_to", None) else None,
            version_id=getattr(row, "version_id", None),
            doc_family_id=getattr(row, "doc_family_id", None),
            metadata=row.metadata or {},
        )

    def get_documents_by_ids(self, doc_ids: Sequence[Any]) -> list[RegulatoryDocumentRecord]:
        if not doc_ids:
            return []
        stmt = text(
            """
            SELECT id, citation, title, jurisdiction, agency, instrument_type,
                   body_text, source_url, content_hash,
                   effective_date, effective_from, effective_to,
                   version_id, doc_family_id, metadata
            FROM regulatory_documents
            WHERE id IN :ids
            """
        ).bindparams(bindparam("ids", expanding=True))
        with self.engine.begin() as conn:
            rows = conn.execute(stmt, {"ids": [coerce_doc_id(v) for v in doc_ids]}).fetchall()
        return [self._row_to_document(row) for row in rows]

    def get_document(self, doc_id: Any) -> RegulatoryDocumentRecord | None:
        stmt = text(
            """
            SELECT id, citation, title, jurisdiction, agency, instrument_type,
                   body_text, source_url, content_hash,
                   effective_date, effective_from, effective_to,
                   version_id, doc_family_id, metadata
            FROM regulatory_documents
            WHERE id = :doc_id
            """
        )
        with self.engine.begin() as conn:
            row = conn.execute(stmt, {"doc_id": coerce_doc_id(doc_id)}).fetchone()
        return self._row_to_document(row) if row else None

    def upsert_chunks(self, chunks: Sequence[RegulatoryChunk]) -> list[RegulatoryChunk]:
        if not chunks:
            return []

        changed: list[RegulatoryChunk] = []
        stmt = text(
            """
            INSERT INTO regulatory_chunks (
                chunk_id, doc_id, node_id, citation, chunk_index, heading_path,
                text, span_start, span_end, chunk_hash, source_doc_hash,
                created_at, updated_at
            ) VALUES (
                :chunk_id, :doc_id, :node_id, :citation, :chunk_index, :heading_path,
                :text, :span_start, :span_end, :chunk_hash, :source_doc_hash,
                :created_at, :updated_at
            )
            ON CONFLICT (chunk_id) DO UPDATE SET
                heading_path = EXCLUDED.heading_path,
                text = EXCLUDED.text,
                span_start = EXCLUDED.span_start,
                span_end = EXCLUDED.span_end,
                chunk_hash = EXCLUDED.chunk_hash,
                source_doc_hash = EXCLUDED.source_doc_hash,
                updated_at = EXCLUDED.updated_at
            WHERE regulatory_chunks.chunk_hash IS DISTINCT FROM EXCLUDED.chunk_hash
               OR regulatory_chunks.source_doc_hash IS DISTINCT FROM EXCLUDED.source_doc_hash
               OR regulatory_chunks.text IS DISTINCT FROM EXCLUDED.text
            RETURNING chunk_id
            """
        )
        with self.engine.begin() as conn:
            for chunk in chunks:
                row = conn.execute(
                    stmt,
                    {
                        "chunk_id": chunk.chunk_id,
                        "doc_id": coerce_doc_id(chunk.doc_id),
                        "node_id": chunk.node_id,
                        "citation": chunk.citation,
                        "chunk_index": chunk.chunk_index,
                        "heading_path": chunk.heading_path,
                        "text": chunk.text,
                        "span_start": chunk.span_start,
                        "span_end": chunk.span_end,
                        "chunk_hash": chunk.chunk_hash,
                        "source_doc_hash": chunk.source_doc_hash,
                        "created_at": chunk.created_at,
                        "updated_at": chunk.updated_at,
                    },
                ).fetchone()
                if row:
                    changed.append(chunk)
        return changed

    def has_obligations_for_chunk_version(
        self,
        chunk_id: str,
        source_doc_hash: str,
        generator_version: str,
    ) -> bool:
        stmt = text(
            """
            SELECT 1
            FROM obligation_cards
            WHERE chunk_id = :chunk_id
              AND source_doc_hash = :source_doc_hash
              AND generated_by->>'generator_version' = :generator_version
            LIMIT 1
            """
        )
        with self.engine.begin() as conn:
            row = conn.execute(
                stmt,
                {
                    "chunk_id": chunk_id,
                    "source_doc_hash": source_doc_hash,
                    "generator_version": generator_version,
                },
            ).fetchone()
        return row is not None

    def upsert_obligations(
        self,
        drafts: Sequence[ObligationCardDraft],
        generator_version: str,
    ) -> list[ObligationCardRecord]:
        if not drafts:
            return []

        inserted: list[ObligationCardRecord] = []
        stmt = text(
            """
            INSERT INTO obligation_cards (
                obligation_id, chunk_id, applies_to, jurisdiction, agency,
                instrument_type, obligation_type, must_do, conditions,
                artifacts_required, exceptions, plain_english_summary,
                grounding, review_status, confidence, generated_by,
                source_doc_hash, created_at
            ) VALUES (
                :obligation_id, :chunk_id, :applies_to, :jurisdiction, :agency,
                :instrument_type, :obligation_type, :must_do, :conditions,
                :artifacts_required, :exceptions, :plain_english_summary,
                CAST(:grounding AS jsonb), :review_status, :confidence, CAST(:generated_by AS jsonb),
                :source_doc_hash, :created_at
            )
            ON CONFLICT (obligation_id) DO UPDATE SET
                applies_to = EXCLUDED.applies_to,
                obligation_type = EXCLUDED.obligation_type,
                must_do = EXCLUDED.must_do,
                conditions = EXCLUDED.conditions,
                artifacts_required = EXCLUDED.artifacts_required,
                exceptions = EXCLUDED.exceptions,
                plain_english_summary = EXCLUDED.plain_english_summary,
                grounding = EXCLUDED.grounding,
                review_status = EXCLUDED.review_status,
                confidence = EXCLUDED.confidence,
                generated_by = EXCLUDED.generated_by,
                source_doc_hash = EXCLUDED.source_doc_hash
            RETURNING obligation_id
            """
        )

        with self.engine.begin() as conn:
            for draft in drafts:
                obligation_id = deterministic_uuid(
                    "obligation-card",
                    draft.chunk_id,
                    draft.must_do,
                    generator_version,
                    draft.source_doc_hash,
                )
                created_at = utcnow()
                conn.execute(
                    stmt,
                    {
                        "obligation_id": str(obligation_id),
                        "chunk_id": draft.chunk_id,
                        "applies_to": draft.applies_to,
                        "jurisdiction": draft.jurisdiction,
                        "agency": draft.agency,
                        "instrument_type": draft.instrument_type,
                        "obligation_type": draft.obligation_type,
                        "must_do": draft.must_do,
                        "conditions": draft.conditions,
                        "artifacts_required": draft.artifacts_required,
                        "exceptions": draft.exceptions,
                        "plain_english_summary": draft.plain_english_summary,
                        "grounding": json.dumps(draft.grounding),
                        "review_status": draft.review_status,
                        "confidence": draft.confidence,
                        "generated_by": json.dumps(
                            {
                                **draft.generated_by,
                                "generator_version": generator_version,
                            }
                        ),
                        "source_doc_hash": draft.source_doc_hash,
                        "created_at": created_at,
                    },
                )
                inserted.append(
                    ObligationCardRecord(
                        obligation_id=obligation_id,
                        chunk_id=draft.chunk_id,
                        applies_to=list(draft.applies_to),
                        jurisdiction=draft.jurisdiction,
                        agency=draft.agency,
                        instrument_type=draft.instrument_type,
                        obligation_type=draft.obligation_type,
                        must_do=draft.must_do,
                        conditions=draft.conditions,
                        artifacts_required=list(draft.artifacts_required),
                        exceptions=draft.exceptions,
                        plain_english_summary=list(draft.plain_english_summary),
                        grounding=dict(draft.grounding),
                        review_status=draft.review_status,
                        confidence=draft.confidence,
                        generated_by={**draft.generated_by, "generator_version": generator_version},
                        source_doc_hash=draft.source_doc_hash,
                        created_at=created_at,
                    )
                )
        return inserted

    def get_chunk(self, chunk_id: str) -> RegulatoryChunk | None:
        stmt = text(
            """
            SELECT chunk_id, doc_id, node_id, citation, chunk_index, heading_path,
                   text, span_start, span_end, chunk_hash, source_doc_hash,
                   created_at, updated_at
            FROM regulatory_chunks
            WHERE chunk_id = :chunk_id
            """
        )
        with self.engine.begin() as conn:
            row = conn.execute(stmt, {"chunk_id": chunk_id}).fetchone()
        if not row:
            return None
        return RegulatoryChunk(
            chunk_id=row.chunk_id,
            doc_id=coerce_doc_id(row.doc_id),
            node_id=row.node_id,
            citation=row.citation,
            chunk_index=row.chunk_index,
            heading_path=row.heading_path,
            text=row.text,
            span_start=row.span_start,
            span_end=row.span_end,
            chunk_hash=row.chunk_hash,
            source_doc_hash=row.source_doc_hash,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def get_obligations_by_ids(self, obligation_ids: Sequence[uuid.UUID]) -> list[ObligationCardRecord]:
        if not obligation_ids:
            return []
        stmt = text(
            """
            SELECT obligation_id, chunk_id, applies_to, jurisdiction, agency,
                   instrument_type, obligation_type, must_do, conditions,
                   artifacts_required, exceptions, plain_english_summary,
                   grounding, review_status, confidence, generated_by,
                   source_doc_hash, created_at
            FROM obligation_cards
            WHERE obligation_id IN :ids
            """
        ).bindparams(bindparam("ids", expanding=True))
        with self.engine.begin() as conn:
            rows = conn.execute(stmt, {"ids": [str(v) for v in obligation_ids]}).fetchall()

        results: list[ObligationCardRecord] = []
        for row in rows:
            results.append(
                ObligationCardRecord(
                    obligation_id=ensure_uuid(row.obligation_id),
                    chunk_id=row.chunk_id,
                    applies_to=list(row.applies_to or []),
                    jurisdiction=row.jurisdiction,
                    agency=row.agency,
                    instrument_type=row.instrument_type,
                    obligation_type=row.obligation_type,
                    must_do=row.must_do,
                    conditions=row.conditions,
                    artifacts_required=list(row.artifacts_required or []),
                    exceptions=row.exceptions,
                    plain_english_summary=list(row.plain_english_summary or []),
                    grounding=row.grounding or {},
                    review_status=row.review_status,
                    confidence=float(row.confidence) if row.confidence is not None else None,
                    generated_by=row.generated_by or {},
                    source_doc_hash=row.source_doc_hash,
                    created_at=row.created_at,
                )
            )
        return results

    def get_obligations_with_context(
        self,
        obligation_ids: Sequence[uuid.UUID],
    ) -> list[dict[str, Any]]:
        if not obligation_ids:
            return []
        stmt = text(
            """
            SELECT
                o.obligation_id,
                o.must_do,
                o.conditions,
                o.artifacts_required,
                o.plain_english_summary,
                o.grounding,
                o.confidence,
                o.review_status,
                o.chunk_id,
                c.text AS chunk_text,
                c.citation,
                d.title,
                d.jurisdiction,
                d.agency,
                d.source_url
            FROM obligation_cards o
            JOIN regulatory_chunks c ON c.chunk_id = o.chunk_id
            LEFT JOIN regulatory_documents d ON d.id = c.doc_id
            WHERE o.obligation_id IN :ids
            """
        ).bindparams(bindparam("ids", expanding=True))
        with self.engine.begin() as conn:
            rows = conn.execute(stmt, {"ids": [str(v) for v in obligation_ids]}).fetchall()
        return [dict(row._mapping) for row in rows]

    def get_latest_rule_map(self, bank_id: str, rule_triggered: str) -> RuleToTypologyMap | None:
        stmt = text(
            """
            SELECT id, bank_id, rule_triggered, typology_id, control_ids,
                   confidence, version, owner
            FROM rule_to_typology_map
            WHERE bank_id = :bank_id AND rule_triggered = :rule_triggered
            ORDER BY created_at DESC, version DESC
            LIMIT 1
            """
        )
        with self.engine.begin() as conn:
            row = conn.execute(stmt, {"bank_id": bank_id, "rule_triggered": rule_triggered}).fetchone()
        if not row:
            return None
        return RuleToTypologyMap(
            id=ensure_uuid(row.id),
            bank_id=row.bank_id,
            rule_triggered=row.rule_triggered,
            typology_id=row.typology_id,
            control_ids=list(row.control_ids) if row.control_ids else None,
            confidence=float(row.confidence) if row.confidence is not None else None,
            version=row.version,
            owner=row.owner,
        )

    def get_typology(self, typology_id: str) -> Typology | None:
        stmt = text(
            """
            SELECT typology_id, name, signals_definition, default_control_ids
            FROM typologies
            WHERE typology_id = :typology_id
            """
        )
        with self.engine.begin() as conn:
            row = conn.execute(stmt, {"typology_id": typology_id}).fetchone()
        if not row:
            return None
        return Typology(
            typology_id=row.typology_id,
            name=row.name,
            signals_definition=row.signals_definition or {},
            default_control_ids=list(row.default_control_ids or []),
        )

    def get_control_objectives(self, control_ids: Sequence[str]) -> list[ControlObjective]:
        if not control_ids:
            return []
        stmt = text(
            """
            SELECT control_id, name, description, expected_artifacts, jurisdiction_scope
            FROM control_objectives
            WHERE control_id IN :ids
            """
        ).bindparams(bindparam("ids", expanding=True))
        with self.engine.begin() as conn:
            rows = conn.execute(stmt, {"ids": list(control_ids)}).fetchall()
        return [
            ControlObjective(
                control_id=row.control_id,
                name=row.name,
                description=row.description,
                expected_artifacts=list(row.expected_artifacts or []),
                jurisdiction_scope=row.jurisdiction_scope,
            )
            for row in rows
        ]

    def get_control_to_obligation_maps(
        self,
        control_ids: Sequence[str],
        jurisdiction_context: str | None = None,
    ) -> list[ControlToObligationMap]:
        if not control_ids:
            return []
        stmt = text(
            """
            SELECT id, control_id, obligation_ids, jurisdiction_filter, priority
            FROM control_to_obligation_map
            WHERE control_id IN :ids
              AND (
                    jurisdiction_filter IS NULL
                 OR lower(jurisdiction_filter) = 'both'
                 OR :jurisdiction_context IS NULL
                 OR :jurisdiction_context ILIKE ('%' || jurisdiction_filter || '%')
              )
            ORDER BY priority DESC, created_at DESC
            """
        ).bindparams(bindparam("ids", expanding=True))
        with self.engine.begin() as conn:
            rows = conn.execute(
                stmt,
                {
                    "ids": list(control_ids),
                    "jurisdiction_context": jurisdiction_context,
                },
            ).fetchall()
        return [
            ControlToObligationMap(
                id=ensure_uuid(row.id),
                control_id=row.control_id,
                obligation_ids=[ensure_uuid(v) for v in (row.obligation_ids or [])],
                jurisdiction_filter=row.jurisdiction_filter,
                priority=row.priority,
            )
            for row in rows
        ]

    def save_proposed_rule_map(self, proposal: ProposedRuleMap) -> None:
        stmt = text(
            """
            INSERT INTO proposed_rule_map (
                id, bank_id, rule_triggered, suggested_typology_id,
                suggested_control_ids, candidate_obligation_ids,
                rationale, status, created_at
            ) VALUES (
                :id, :bank_id, :rule_triggered, :suggested_typology_id,
                :suggested_control_ids, CAST(:candidate_obligation_ids AS uuid[]),
                CAST(:rationale AS jsonb), :status, :created_at
            )
            """
        )
        with self.engine.begin() as conn:
            conn.execute(
                stmt,
                {
                    "id": str(uuid.uuid4()),
                    "bank_id": proposal.bank_id,
                    "rule_triggered": proposal.rule_triggered,
                    "suggested_typology_id": proposal.suggested_typology_id,
                    "suggested_control_ids": proposal.suggested_control_ids,
                    "candidate_obligation_ids": [str(v) for v in proposal.candidate_obligation_ids],
                    "rationale": json.dumps(proposal.rationale),
                    "status": proposal.status,
                    "created_at": utcnow(),
                },
            )

    def search_obligations_text(
        self,
        query: str,
        top_k: int,
        jurisdiction: str | None = None,
        agency: str | None = None,
        instrument_type: str | None = None,
    ) -> list[dict[str, Any]]:
        stmt = text(
            """
            SELECT
                o.obligation_id,
                o.must_do,
                o.conditions,
                o.artifacts_required,
                o.plain_english_summary,
                o.grounding,
                o.confidence,
                o.review_status,
                o.chunk_id,
                c.text AS excerpt,
                c.citation,
                d.title,
                d.source_url,
                d.jurisdiction,
                d.agency,
                d.instrument_type,
                (
                    CASE
                        WHEN lower(o.must_do) LIKE lower(:like_q) THEN 5
                        ELSE 0
                    END +
                    CASE
                        WHEN lower(c.text) LIKE lower(:like_q) THEN 2
                        ELSE 0
                    END
                ) AS rank_score
            FROM obligation_cards o
            JOIN regulatory_chunks c ON c.chunk_id = o.chunk_id
            LEFT JOIN regulatory_documents d ON d.id = c.doc_id
            WHERE (
                lower(o.must_do) LIKE lower(:like_q)
                OR lower(coalesce(o.conditions, '')) LIKE lower(:like_q)
                OR lower(c.text) LIKE lower(:like_q)
                OR lower(array_to_string(o.plain_english_summary, ' ')) LIKE lower(:like_q)
            )
            AND (:jurisdiction IS NULL OR d.jurisdiction = :jurisdiction)
            AND (:agency IS NULL OR d.agency = :agency)
            AND (:instrument_type IS NULL OR d.instrument_type = :instrument_type)
            ORDER BY rank_score DESC, o.created_at DESC
            LIMIT :top_k
            """
        )
        with self.engine.begin() as conn:
            rows = conn.execute(
                stmt,
                {
                    "like_q": f"%{query}%",
                    "jurisdiction": jurisdiction,
                    "agency": agency,
                    "instrument_type": instrument_type,
                    "top_k": top_k,
                },
            ).fetchall()
        return [dict(row._mapping) for row in rows]

    def upsert_control_objective(self, control: ControlObjective) -> None:
        stmt = text(
            """
            INSERT INTO control_objectives (
                control_id, name, description, expected_artifacts,
                jurisdiction_scope, created_at
            ) VALUES (
                :control_id, :name, :description, :expected_artifacts,
                :jurisdiction_scope, :created_at
            )
            ON CONFLICT (control_id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                expected_artifacts = EXCLUDED.expected_artifacts,
                jurisdiction_scope = EXCLUDED.jurisdiction_scope
            """
        )
        with self.engine.begin() as conn:
            conn.execute(
                stmt,
                {
                    "control_id": control.control_id,
                    "name": control.name,
                    "description": control.description,
                    "expected_artifacts": control.expected_artifacts,
                    "jurisdiction_scope": control.jurisdiction_scope,
                    "created_at": utcnow(),
                },
            )

    def upsert_typology(self, typology: Typology) -> None:
        stmt = text(
            """
            INSERT INTO typologies (
                typology_id, name, signals_definition, default_control_ids,
                created_at
            ) VALUES (
                :typology_id, :name, CAST(:signals_definition AS jsonb), :default_control_ids,
                :created_at
            )
            ON CONFLICT (typology_id) DO UPDATE SET
                name = EXCLUDED.name,
                signals_definition = EXCLUDED.signals_definition,
                default_control_ids = EXCLUDED.default_control_ids
            """
        )
        with self.engine.begin() as conn:
            conn.execute(
                stmt,
                {
                    "typology_id": typology.typology_id,
                    "name": typology.name,
                    "signals_definition": json.dumps(typology.signals_definition),
                    "default_control_ids": typology.default_control_ids,
                    "created_at": utcnow(),
                },
            )

    def upsert_rule_map(self, mapping: RuleToTypologyMap) -> None:
        stmt = text(
            """
            INSERT INTO rule_to_typology_map (
                id, bank_id, rule_triggered, typology_id,
                control_ids, confidence, version, owner,
                created_at
            ) VALUES (
                :id, :bank_id, :rule_triggered, :typology_id,
                :control_ids, :confidence, :version, :owner,
                :created_at
            )
            ON CONFLICT (bank_id, rule_triggered, version) DO UPDATE SET
                typology_id = EXCLUDED.typology_id,
                control_ids = EXCLUDED.control_ids,
                confidence = EXCLUDED.confidence,
                owner = EXCLUDED.owner
            """
        )
        with self.engine.begin() as conn:
            conn.execute(
                stmt,
                {
                    "id": str(mapping.id),
                    "bank_id": mapping.bank_id,
                    "rule_triggered": mapping.rule_triggered,
                    "typology_id": mapping.typology_id,
                    "control_ids": mapping.control_ids,
                    "confidence": mapping.confidence,
                    "version": mapping.version,
                    "owner": mapping.owner,
                    "created_at": utcnow(),
                },
            )

    def upsert_control_to_obligation_map(self, mapping: ControlToObligationMap) -> None:
        stmt = text(
            """
            INSERT INTO control_to_obligation_map (
                id, control_id, obligation_ids,
                jurisdiction_filter, priority, created_at
            ) VALUES (
                :id, :control_id, CAST(:obligation_ids AS uuid[]),
                :jurisdiction_filter, :priority, :created_at
            )
            ON CONFLICT (id) DO UPDATE SET
                obligation_ids = EXCLUDED.obligation_ids,
                jurisdiction_filter = EXCLUDED.jurisdiction_filter,
                priority = EXCLUDED.priority
            """
        )
        with self.engine.begin() as conn:
            conn.execute(
                stmt,
                {
                    "id": str(mapping.id),
                    "control_id": mapping.control_id,
                    "obligation_ids": [str(v) for v in mapping.obligation_ids],
                    "jurisdiction_filter": mapping.jurisdiction_filter,
                    "priority": mapping.priority,
                    "created_at": utcnow(),
                },
            )


class InMemoryLawRepository:
    """Simple repository used by tests and local offline development."""

    def __init__(self):
        self.documents: dict[Any, RegulatoryDocumentRecord] = {}
        self.chunks: dict[str, RegulatoryChunk] = {}
        self.obligations: dict[uuid.UUID, ObligationCardRecord] = {}
        self.controls: dict[str, ControlObjective] = {}
        self.typologies: dict[str, Typology] = {}
        self.rule_maps: list[RuleToTypologyMap] = []
        self.control_to_obligation_maps: list[ControlToObligationMap] = []
        self.proposed_maps: list[ProposedRuleMap] = []

    def add_document(self, doc: RegulatoryDocumentRecord) -> None:
        self.documents[doc.id] = doc

    def get_documents_by_ids(self, doc_ids: Sequence[Any]) -> list[RegulatoryDocumentRecord]:
        return [self.documents[doc_id] for doc_id in doc_ids if doc_id in self.documents]

    def get_document(self, doc_id: Any) -> RegulatoryDocumentRecord | None:
        return self.documents.get(doc_id)

    def upsert_chunks(self, chunks: Sequence[RegulatoryChunk]) -> list[RegulatoryChunk]:
        changed: list[RegulatoryChunk] = []
        for chunk in chunks:
            existing = self.chunks.get(chunk.chunk_id)
            if existing is None or existing.chunk_hash != chunk.chunk_hash or existing.text != chunk.text:
                self.chunks[chunk.chunk_id] = chunk
                changed.append(chunk)
        return changed

    def get_chunk(self, chunk_id: str) -> RegulatoryChunk | None:
        return self.chunks.get(chunk_id)

    def has_obligations_for_chunk_version(
        self,
        chunk_id: str,
        source_doc_hash: str,
        generator_version: str,
    ) -> bool:
        for obligation in self.obligations.values():
            if (
                obligation.chunk_id == chunk_id
                and obligation.source_doc_hash == source_doc_hash
                and obligation.generated_by.get("generator_version") == generator_version
            ):
                return True
        return False

    def upsert_obligations(
        self,
        drafts: Sequence[ObligationCardDraft],
        generator_version: str,
    ) -> list[ObligationCardRecord]:
        inserted: list[ObligationCardRecord] = []
        for draft in drafts:
            obligation_id = deterministic_uuid(
                "obligation-card",
                draft.chunk_id,
                draft.must_do,
                generator_version,
                draft.source_doc_hash,
            )
            card = ObligationCardRecord(
                obligation_id=obligation_id,
                chunk_id=draft.chunk_id,
                applies_to=list(draft.applies_to),
                jurisdiction=draft.jurisdiction,
                agency=draft.agency,
                instrument_type=draft.instrument_type,
                obligation_type=draft.obligation_type,
                must_do=draft.must_do,
                conditions=draft.conditions,
                artifacts_required=list(draft.artifacts_required),
                exceptions=draft.exceptions,
                plain_english_summary=list(draft.plain_english_summary),
                grounding=dict(draft.grounding),
                review_status=draft.review_status,
                confidence=draft.confidence,
                generated_by={**draft.generated_by, "generator_version": generator_version},
                source_doc_hash=draft.source_doc_hash,
                created_at=utcnow(),
            )
            self.obligations[obligation_id] = card
            inserted.append(card)
        return inserted

    def get_obligations_by_ids(self, obligation_ids: Sequence[uuid.UUID]) -> list[ObligationCardRecord]:
        return [self.obligations[ob_id] for ob_id in obligation_ids if ob_id in self.obligations]

    def get_obligations_with_context(
        self,
        obligation_ids: Sequence[uuid.UUID],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for obligation_id in obligation_ids:
            card = self.obligations.get(obligation_id)
            if not card:
                continue
            chunk = self.chunks.get(card.chunk_id)
            if not chunk:
                continue
            doc = self.documents.get(chunk.doc_id)
            rows.append(
                {
                    "obligation_id": card.obligation_id,
                    "must_do": card.must_do,
                    "conditions": card.conditions,
                    "artifacts_required": card.artifacts_required,
                    "plain_english_summary": card.plain_english_summary,
                    "grounding": card.grounding,
                    "confidence": card.confidence,
                    "review_status": card.review_status,
                    "chunk_id": card.chunk_id,
                    "chunk_text": chunk.text,
                    "citation": chunk.citation,
                    "title": doc.title if doc else "",
                    "jurisdiction": doc.jurisdiction if doc else card.jurisdiction,
                    "agency": doc.agency if doc else card.agency,
                    "source_url": doc.source_url if doc else None,
                }
            )
        return rows

    def get_latest_rule_map(self, bank_id: str, rule_triggered: str) -> RuleToTypologyMap | None:
        matches = [
            mapping
            for mapping in self.rule_maps
            if mapping.bank_id == bank_id and mapping.rule_triggered == rule_triggered
        ]
        if not matches:
            return None
        matches.sort(key=lambda value: value.version)
        return matches[-1]

    def get_typology(self, typology_id: str) -> Typology | None:
        return self.typologies.get(typology_id)

    def get_control_objectives(self, control_ids: Sequence[str]) -> list[ControlObjective]:
        return [self.controls[control_id] for control_id in control_ids if control_id in self.controls]

    def get_control_to_obligation_maps(
        self,
        control_ids: Sequence[str],
        jurisdiction_context: str | None = None,
    ) -> list[ControlToObligationMap]:
        results: list[ControlToObligationMap] = []
        ctx = (jurisdiction_context or "").lower()
        for mapping in self.control_to_obligation_maps:
            if mapping.control_id not in control_ids:
                continue
            if (
                mapping.jurisdiction_filter
                and mapping.jurisdiction_filter.lower() != "both"
                and mapping.jurisdiction_filter.lower() not in ctx
            ):
                continue
            results.append(mapping)
        results.sort(key=lambda value: value.priority, reverse=True)
        return results

    def save_proposed_rule_map(self, proposal: ProposedRuleMap) -> None:
        self.proposed_maps.append(proposal)

    def search_obligations_text(
        self,
        query: str,
        top_k: int,
        jurisdiction: str | None = None,
        agency: str | None = None,
        instrument_type: str | None = None,
    ) -> list[dict[str, Any]]:
        query_l = query.lower().strip()
        if not query_l:
            return []

        scored: list[tuple[int, dict[str, Any]]] = []
        for card in self.obligations.values():
            chunk = self.chunks.get(card.chunk_id)
            if not chunk:
                continue
            doc = self.documents.get(chunk.doc_id)
            if jurisdiction and doc and doc.jurisdiction != jurisdiction:
                continue
            if agency and doc and doc.agency != agency:
                continue
            if instrument_type and doc and doc.instrument_type != instrument_type:
                continue

            haystack = " ".join(
                [
                    card.must_do,
                    card.conditions or "",
                    " ".join(card.plain_english_summary),
                    chunk.text,
                ]
            ).lower()
            score = haystack.count(query_l)
            if score <= 0:
                continue
            scored.append(
                (
                    score,
                    {
                        "obligation_id": card.obligation_id,
                        "must_do": card.must_do,
                        "conditions": card.conditions,
                        "artifacts_required": list(card.artifacts_required),
                        "plain_english_summary": list(card.plain_english_summary),
                        "grounding": dict(card.grounding),
                        "confidence": card.confidence,
                        "review_status": card.review_status,
                        "chunk_id": card.chunk_id,
                        "excerpt": chunk.text,
                        "citation": chunk.citation,
                        "title": doc.title if doc else "",
                        "source_url": doc.source_url if doc else None,
                        "jurisdiction": doc.jurisdiction if doc else card.jurisdiction,
                        "agency": doc.agency if doc else card.agency,
                        "instrument_type": doc.instrument_type if doc else card.instrument_type,
                    },
                )
            )
        scored.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in scored[:top_k]]

    def upsert_control_objective(self, control: ControlObjective) -> None:
        self.controls[control.control_id] = control

    def upsert_typology(self, typology: Typology) -> None:
        self.typologies[typology.typology_id] = typology

    def upsert_rule_map(self, mapping: RuleToTypologyMap) -> None:
        self.rule_maps.append(mapping)

    def upsert_control_to_obligation_map(self, mapping: ControlToObligationMap) -> None:
        self.control_to_obligation_maps.append(mapping)


def create_sql_repository(database_url: str | None = None) -> SQLLawRepository:
    return SQLLawRepository(database_url=database_url or settings.database_url)
