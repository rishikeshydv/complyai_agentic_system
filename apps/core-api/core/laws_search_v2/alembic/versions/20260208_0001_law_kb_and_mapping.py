"""Add law knowledge base and law-mapping tables.

Revision ID: 20260208_0001
Revises: None
Create Date: 2026-02-08 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260208_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "regulatory_chunks",
        sa.Column("chunk_id", sa.Text(), primary_key=True),
        sa.Column("doc_id", sa.Integer(), sa.ForeignKey("regulatory_documents.id"), nullable=False),
        sa.Column("node_id", sa.Text(), nullable=False),
        sa.Column("citation", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("heading_path", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("span_start", sa.Integer(), nullable=True),
        sa.Column("span_end", sa.Integer(), nullable=True),
        sa.Column("chunk_hash", sa.Text(), nullable=False),
        sa.Column("source_doc_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_regulatory_chunks_doc_id", "regulatory_chunks", ["doc_id"])
    op.create_index("idx_regulatory_chunks_citation", "regulatory_chunks", ["citation"])
    op.create_index("idx_regulatory_chunks_node_id", "regulatory_chunks", ["node_id"])

    op.create_table(
        "obligation_cards",
        sa.Column("obligation_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("chunk_id", sa.Text(), sa.ForeignKey("regulatory_chunks.chunk_id"), nullable=False),
        sa.Column("applies_to", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("jurisdiction", sa.Text(), nullable=False),
        sa.Column("agency", sa.Text(), nullable=False),
        sa.Column("instrument_type", sa.Text(), nullable=False),
        sa.Column("obligation_type", sa.Text(), nullable=False),
        sa.Column("must_do", sa.Text(), nullable=False),
        sa.Column("conditions", sa.Text(), nullable=True),
        sa.Column("artifacts_required", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("exceptions", sa.Text(), nullable=True),
        sa.Column("plain_english_summary", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("grounding", postgresql.JSONB(), nullable=False),
        sa.Column("review_status", sa.Text(), nullable=False, server_default="unreviewed"),
        sa.Column("confidence", sa.Numeric(), nullable=True),
        sa.Column("generated_by", postgresql.JSONB(), nullable=False),
        sa.Column("source_doc_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_obligation_cards_chunk_id", "obligation_cards", ["chunk_id"])
    op.create_index(
        "idx_obligation_cards_plain_english_summary_gin",
        "obligation_cards",
        ["plain_english_summary"],
        postgresql_using="gin",
    )
    op.create_index(
        "idx_obligation_cards_artifacts_required_gin",
        "obligation_cards",
        ["artifacts_required"],
        postgresql_using="gin",
    )

    op.create_table(
        "control_objectives",
        sa.Column("control_id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("expected_artifacts", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("jurisdiction_scope", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "typologies",
        sa.Column("typology_id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("signals_definition", postgresql.JSONB(), nullable=False),
        sa.Column("default_control_ids", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "rule_to_typology_map",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bank_id", sa.Text(), nullable=False),
        sa.Column("rule_triggered", sa.Text(), nullable=False),
        sa.Column("typology_id", sa.Text(), sa.ForeignKey("typologies.typology_id"), nullable=False),
        sa.Column("control_ids", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("confidence", sa.Numeric(), nullable=True),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("owner", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "uq_rule_to_typology_map_bank_rule_version",
        "rule_to_typology_map",
        ["bank_id", "rule_triggered", "version"],
        unique=True,
    )

    op.create_table(
        "control_to_obligation_map",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("control_id", sa.Text(), sa.ForeignKey("control_objectives.control_id"), nullable=False),
        sa.Column("obligation_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False),
        sa.Column("jurisdiction_filter", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "proposed_rule_map",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bank_id", sa.Text(), nullable=False),
        sa.Column("rule_triggered", sa.Text(), nullable=False),
        sa.Column("suggested_typology_id", sa.Text(), nullable=True),
        sa.Column("suggested_control_ids", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("candidate_obligation_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False),
        sa.Column("rationale", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("proposed_rule_map")
    op.drop_table("control_to_obligation_map")
    op.drop_index("uq_rule_to_typology_map_bank_rule_version", table_name="rule_to_typology_map")
    op.drop_table("rule_to_typology_map")
    op.drop_table("typologies")
    op.drop_table("control_objectives")
    op.drop_index("idx_obligation_cards_artifacts_required_gin", table_name="obligation_cards")
    op.drop_index("idx_obligation_cards_plain_english_summary_gin", table_name="obligation_cards")
    op.drop_index("idx_obligation_cards_chunk_id", table_name="obligation_cards")
    op.drop_table("obligation_cards")
    op.drop_index("idx_regulatory_chunks_node_id", table_name="regulatory_chunks")
    op.drop_index("idx_regulatory_chunks_citation", table_name="regulatory_chunks")
    op.drop_index("idx_regulatory_chunks_doc_id", table_name="regulatory_chunks")
    op.drop_table("regulatory_chunks")
