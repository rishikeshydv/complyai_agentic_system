from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    workflow_run_id = Column(String, primary_key=True)
    alert_id = Column(String, nullable=False)
    bank_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    steps = Column(JSON, nullable=False, default=list)
    errors = Column(JSON, nullable=False, default=list)
    request_id = Column(String, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    case_id = Column(String, nullable=True)


class EvidenceSnapshot(Base):
    __tablename__ = "evidence_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String, nullable=True)
    alert_id = Column(String, nullable=False)
    bank_id = Column(String, nullable=False)
    graph_json = Column(JSON, nullable=False)
    evidence_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Case(Base):
    __tablename__ = "cases"

    case_id = Column(String, primary_key=True)
    alert_id = Column(String, nullable=False)
    bank_id = Column(String, nullable=False)
    alert_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    casefile_json = Column(JSON, nullable=False)
    casefile_markdown = Column(Text, nullable=False)
    evidence_snapshot_id = Column(Integer, ForeignKey("evidence_snapshots.id"), nullable=False)
    evidence_hash = Column(String, nullable=False)
    casefile_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String, unique=True, nullable=False)
    case_id = Column(String, nullable=True)
    workflow_run_id = Column(String, nullable=True)
    actor_type = Column(String, nullable=False)
    actor_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    notes = Column(Text, nullable=False)
    metadata_jsonb = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class RegulatoryMapping(Base):
    __tablename__ = "regulatory_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bank_id = Column(String, nullable=False, default="default")
    alert_type = Column(String, nullable=False)
    rule_triggered = Column(String, nullable=False)
    citation_ids = Column(JSON, nullable=False)
    why_relevant_template = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class RegulatoryTypology(Base):
    __tablename__ = "regulatory_typologies"

    typology_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    signals_definition = Column(JSON, nullable=False, default=dict)
    default_control_ids = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class RegulatoryControlObjective(Base):
    __tablename__ = "regulatory_control_objectives"

    control_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    expected_artifacts = Column(JSON, nullable=False, default=list)
    jurisdiction_scope = Column(String, nullable=False, default="federal")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ControlCitationMap(Base):
    __tablename__ = "control_citation_maps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    control_id = Column(String, ForeignKey("regulatory_control_objectives.control_id"), nullable=False)
    citation_ids = Column(JSON, nullable=False, default=list)
    jurisdiction_filter = Column(String, nullable=True)
    priority = Column(Integer, nullable=False, default=100)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class RegulatoryRuleMap(Base):
    __tablename__ = "regulatory_rule_maps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bank_id = Column(String, nullable=False, default="default")
    alert_type = Column(String, nullable=False)
    rule_triggered = Column(String, nullable=False)
    typology_id = Column(String, ForeignKey("regulatory_typologies.typology_id"), nullable=True)
    control_ids = Column(JSON, nullable=True)
    citation_ids = Column(JSON, nullable=True)
    confidence = Column(String, nullable=True)
    version = Column(String, nullable=False, default="v1")
    owner = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ProposedRuleMap(Base):
    __tablename__ = "proposed_rule_maps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bank_id = Column(String, nullable=False, default="default")
    alert_type = Column(String, nullable=False)
    rule_triggered = Column(String, nullable=False)
    candidate_citation_ids = Column(JSON, nullable=False, default=list)
    rationale = Column(JSON, nullable=False, default=dict)
    status = Column(String, nullable=False, default="PENDING_REVIEW")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class LawCitation(Base):
    __tablename__ = "law_citations"

    citation_id = Column(String, primary_key=True)
    alert_type = Column(String, nullable=False)
    jurisdiction = Column(String, nullable=False)
    title = Column(String, nullable=False)
    text_snippet = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class LLMInvocation(Base):
    __tablename__ = "llm_invocations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_run_id = Column(String, nullable=True)
    case_id = Column(String, nullable=True)
    prompt_id = Column(String, nullable=False)
    version = Column(String, nullable=False)
    rendered_prompt_hash = Column(String, nullable=False)
    model_provider = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    response_hash = Column(String, nullable=False)
    request_payload = Column(JSON, nullable=True)
    response_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ConnectorPollState(Base):
    __tablename__ = "connector_poll_state"

    bank_id = Column(String, primary_key=True)
    last_seen_created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AlertIngestEvent(Base):
    __tablename__ = "alert_ingest_events"
    __table_args__ = (
        UniqueConstraint("bank_id", "alert_id", "source_event_id", name="uq_alert_ingest_event"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    bank_id = Column(String, nullable=False)
    alert_id = Column(String, nullable=False)
    source_event_id = Column(String, nullable=False)
    event_created_at = Column(DateTime, nullable=True)
    workflow_run_id = Column(String, nullable=True)
    case_id = Column(String, nullable=True)
    status = Column(String, nullable=False, default="QUEUED")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class PilotLead(Base):
    __tablename__ = "pilot_leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    company = Column(String, nullable=True)
    requester_name = Column(String, nullable=True)
    requester_email = Column(String, nullable=False)

    alert_engine_or_case_tool = Column(String, nullable=True)
    alert_types = Column(JSON, nullable=False, default=list)
    monthly_alert_volume = Column(Integer, nullable=True)

    it_contact_name = Column(String, nullable=True)
    it_contact_email = Column(String, nullable=True)
    message = Column(Text, nullable=True)

    metadata_json = Column(JSON, nullable=False, default=dict)
