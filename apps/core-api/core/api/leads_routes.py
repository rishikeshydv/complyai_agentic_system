from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core.db.models import PilotLead
from core.db.session import get_db
from core.schemas.leads import PilotLeadRequest, PilotLeadResponse
from core.utils.request_context import request_id_ctx

router = APIRouter(prefix="/v1/leads", tags=["leads"])


@router.post("/pilot", response_model=PilotLeadResponse)
def create_pilot_lead(payload: PilotLeadRequest, request: Request, db: Session = Depends(get_db)) -> PilotLeadResponse:
    row = PilotLead(
        company=payload.company,
        requester_name=payload.requester_name,
        requester_email=str(payload.requester_email),
        alert_engine_or_case_tool=payload.alert_engine_or_case_tool,
        alert_types=payload.alert_types,
        monthly_alert_volume=payload.monthly_alert_volume,
        it_contact_name=payload.it_contact_name,
        it_contact_email=str(payload.it_contact_email) if payload.it_contact_email else None,
        message=payload.message,
        metadata_json={
            **(payload.metadata or {}),
            "request_id": request_id_ctx.get(),
            "user_agent": request.headers.get("user-agent", ""),
        },
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return PilotLeadResponse(id=row.id)
