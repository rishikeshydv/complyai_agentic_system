from __future__ import annotations

from pydantic import BaseModel


class RegulatoryMappingIn(BaseModel):
    bank_id: str = "default"
    alert_type: str
    rule_triggered: str
    citation_ids: list[str]
    why_relevant_template: str


class RegulatoryMappingOut(RegulatoryMappingIn):
    id: int


class RegulatoryRuleMapIn(BaseModel):
    bank_id: str = "default"
    alert_type: str
    rule_triggered: str
    typology_id: str | None = None
    control_ids: list[str] | None = None
    citation_ids: list[str] | None = None
    confidence: str | None = None
    version: str = "v1"
    owner: str | None = None


class RegulatoryRuleMapOut(RegulatoryRuleMapIn):
    id: int
