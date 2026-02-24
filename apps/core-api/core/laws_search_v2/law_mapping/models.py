from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field


class ConditionTriggered(BaseModel):
    field: str
    operator: str
    threshold: float | str | None = None
    actual: float | str | None = None
    window_days: int | None = None


class Event(BaseModel):
    bank_id: str
    event_id: str = Field(alias="alert_id", default="")
    event_type: Literal["AML_ALERT", "SANCTIONS_ALERT", "VIOLATION"]
    rule_triggered: str
    rule_description: str
    conditions_triggered: list[ConditionTriggered] = Field(default_factory=list)
    jurisdiction_context: str
    metadata: dict[str, Any] | None = None

    class Config:
        populate_by_name = True


class ControlResult(BaseModel):
    control_id: str
    name: str


class ObligationResult(BaseModel):
    obligation_id: uuid.UUID
    must_do: str
    conditions: str | None
    artifacts_required: list[str]
    summary_bullets: list[str]
    grounding: dict[str, Any]


class CitationResult(BaseModel):
    citation: str
    title: str
    jurisdiction: str
    agency: str
    excerpt: str
    source_url: str | None = None
    why_relevant: str


class MappingResult(BaseModel):
    event_id: str
    mapping_mode: Literal["deterministic", "fallback", "none"]
    controls: list[ControlResult]
    obligations: list[ObligationResult]
    citations: list[CitationResult]


@dataclass(frozen=True)
class ControlObjective:
    control_id: str
    name: str
    description: str
    expected_artifacts: list[str]
    jurisdiction_scope: str


@dataclass(frozen=True)
class Typology:
    typology_id: str
    name: str
    signals_definition: dict[str, Any]
    default_control_ids: list[str]


@dataclass(frozen=True)
class RuleToTypologyMap:
    id: uuid.UUID
    bank_id: str
    rule_triggered: str
    typology_id: str
    control_ids: list[str] | None
    confidence: float | None
    version: str
    owner: str | None


@dataclass(frozen=True)
class ControlToObligationMap:
    id: uuid.UUID
    control_id: str
    obligation_ids: list[uuid.UUID]
    jurisdiction_filter: str | None
    priority: int


@dataclass
class ProposedRuleMap:
    bank_id: str
    rule_triggered: str
    suggested_typology_id: str | None
    suggested_control_ids: list[str]
    candidate_obligation_ids: list[uuid.UUID]
    rationale: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
