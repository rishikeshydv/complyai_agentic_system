from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PilotLeadRequest(BaseModel):
    company: str | None = Field(default=None, max_length=200)
    requester_name: str | None = Field(default=None, max_length=200)
    requester_email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    alert_engine_or_case_tool: str | None = Field(default=None, max_length=300)
    alert_types: list[str] = Field(default_factory=list, max_length=10)
    monthly_alert_volume: int | None = Field(default=None, ge=0, le=10_000_000)

    it_contact_name: str | None = Field(default=None, max_length=200)
    it_contact_email: str | None = Field(default=None, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    message: str | None = Field(default=None, max_length=4000)

    # Extra form context (utm, page, etc.)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PilotLeadResponse(BaseModel):
    id: int
    status: str = "ok"
