from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PlaygroundStartRequest(BaseModel):
    bank_id: str = "demo"
    seed_customers: int = Field(default=20, ge=1, le=200)
    tx_per_tick: int = Field(default=12, ge=1, le=100)
    aml_alert_rate: float = Field(default=0.2, ge=0, le=1)
    sanctions_alert_rate: float = Field(default=0.05, ge=0, le=1)
    reset_before_start: bool = True


class PlaygroundTickRequest(BaseModel):
    bank_id: str = "demo"
    count: int = Field(default=1, ge=1, le=50)
    run_ingestion_poll: bool = True


class PlaygroundStatusResponse(BaseModel):
    bank_id: str
    simulator: dict[str, Any]
    pipeline: dict[str, Any]
