from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RegulatoryChunkModel(Base):
    __tablename__ = "regulatory_chunks"

    chunk_id: Mapped[str] = mapped_column(Text, primary_key=True)
    doc_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("regulatory_documents.id"),
        nullable=False,
    )
    node_id: Mapped[str] = mapped_column(Text, nullable=False)
    citation: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    heading_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    span_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    span_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_hash: Mapped[str] = mapped_column(Text, nullable=False)
    source_doc_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index("idx_regulatory_chunks_doc_id", RegulatoryChunkModel.doc_id)
Index("idx_regulatory_chunks_citation", RegulatoryChunkModel.citation)
Index("idx_regulatory_chunks_node_id", RegulatoryChunkModel.node_id)


class ObligationCardModel(Base):
    __tablename__ = "obligation_cards"

    obligation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id: Mapped[str] = mapped_column(Text, ForeignKey("regulatory_chunks.chunk_id"), nullable=False)
    applies_to: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    jurisdiction: Mapped[str] = mapped_column(Text, nullable=False)
    agency: Mapped[str] = mapped_column(Text, nullable=False)
    instrument_type: Mapped[str] = mapped_column(Text, nullable=False)
    obligation_type: Mapped[str] = mapped_column(Text, nullable=False)
    must_do: Mapped[str] = mapped_column(Text, nullable=False)
    conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifacts_required: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    exceptions: Mapped[str | None] = mapped_column(Text, nullable=True)
    plain_english_summary: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    grounding: Mapped[dict] = mapped_column(JSONB, nullable=False)
    review_status: Mapped[str] = mapped_column(Text, nullable=False, default="unreviewed")
    confidence: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    generated_by: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source_doc_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


Index("idx_obligation_cards_chunk_id", ObligationCardModel.chunk_id)
Index(
    "idx_obligation_cards_plain_english_summary_gin",
    ObligationCardModel.plain_english_summary,
    postgresql_using="gin",
)
Index(
    "idx_obligation_cards_artifacts_required_gin",
    ObligationCardModel.artifacts_required,
    postgresql_using="gin",
)


class ControlObjectiveModel(Base):
    __tablename__ = "control_objectives"

    control_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    expected_artifacts: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    jurisdiction_scope: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class TypologyModel(Base):
    __tablename__ = "typologies"

    typology_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    signals_definition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    default_control_ids: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RuleToTypologyMapModel(Base):
    __tablename__ = "rule_to_typology_map"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_id: Mapped[str] = mapped_column(Text, nullable=False)
    rule_triggered: Mapped[str] = mapped_column(Text, nullable=False)
    typology_id: Mapped[str] = mapped_column(Text, ForeignKey("typologies.typology_id"), nullable=False)
    control_ids: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


Index(
    "uq_rule_to_typology_map_bank_rule_version",
    RuleToTypologyMapModel.bank_id,
    RuleToTypologyMapModel.rule_triggered,
    RuleToTypologyMapModel.version,
    unique=True,
)


class ControlToObligationMapModel(Base):
    __tablename__ = "control_to_obligation_map"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    control_id: Mapped[str] = mapped_column(Text, ForeignKey("control_objectives.control_id"), nullable=False)
    obligation_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    jurisdiction_filter: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ProposedRuleMapModel(Base):
    __tablename__ = "proposed_rule_map"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_id: Mapped[str] = mapped_column(Text, nullable=False)
    rule_triggered: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_typology_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_control_ids: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    candidate_obligation_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    rationale: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
