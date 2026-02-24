from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CaseRecord(BaseModel):
    case_id: str
    alert_id: str
    bank_id: str
    alert_type: str
    status: str
    casefile_json: dict[str, Any]
    casefile_markdown: str
    created_at: datetime
    updated_at: datetime
    integrity: dict[str, str]


class PullAlertResponse(BaseModel):
    workflow_run_id: str
    status: str
    case_id: str | None = None


class IngestionPollResponse(BaseModel):
    enabled: bool
    queued: int
    deduped: int
    errors: int
    discovered: int
    banks: list[dict[str, Any]]


class AlertEventRequest(BaseModel):
    bank_id: str = "demo"
    alert_id: str
    source_event_id: str
    created_at: str | None = None


class CaseActionRequest(BaseModel):
    action: str
    actor_id: str
    notes: str | None = None
    sar_narrative: str | None = None


class ReplayResponse(BaseModel):
    case_id: str
    old_casefile_hash: str
    new_casefile_hash: str
    diff: str
    applied: bool
