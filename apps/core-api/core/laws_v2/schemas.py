from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ConditionTriggered(BaseModel):
    field: str
    operator: str
    threshold: float | str | None = None
    actual: float | str | None = None
    window_days: int | None = None


class Event(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    bank_id: str = "default"
    event_id: str = Field(alias="alert_id", default="")
    event_type: Literal["AML_ALERT", "SANCTIONS_ALERT", "VIOLATION"]
    rule_triggered: str
    rule_description: str = "NOT PROVIDED"
    conditions_triggered: list[ConditionTriggered] = Field(default_factory=list)
    jurisdiction_context: str = "federal"
    metadata: dict[str, Any] | None = None


class ControlResult(BaseModel):
    control_id: str
    name: str


class ObligationResult(BaseModel):
    obligation_id: str
    must_do: str
    conditions: str | None
    artifacts_required: list[str]
    summary_bullets: list[str]
    grounding: dict[str, Any]


class CitationResult(BaseModel):
    citation_id: str
    title: str
    jurisdiction: str
    text_snippet: str | None = None
    why_relevant: str
    evidence_pointers: list[str]
    mapping_mode: str
    typology_id: str | None = None


class MappingResult(BaseModel):
    event_id: str
    mapping_mode: Literal["deterministic", "fallback", "none"]
    controls: list[ControlResult]
    obligations: list[ObligationResult]
    citations: list[CitationResult]


class SearchResult(BaseModel):
    citation_id: str
    alert_type: str
    title: str
    jurisdiction: str
    text_snippet: str | None = None
    score: float
    mapping_context: dict[str, Any]


class SearchResponse(BaseModel):
    total: int
    results: list[SearchResult]
