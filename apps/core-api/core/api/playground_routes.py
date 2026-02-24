from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.db.session import get_db
from core.schemas.playground import PlaygroundStartRequest, PlaygroundStatusResponse, PlaygroundTickRequest
from core.services.playground_service import PlaygroundService

router = APIRouter(prefix="/v1/playground", tags=["playground"])


@router.get("/status", response_model=PlaygroundStatusResponse)
def playground_status(
    bank_id: str = Query(default="demo"),
    db: Session = Depends(get_db),
):
    service = PlaygroundService()
    result = service.status(db=db, bank_id=bank_id)
    return PlaygroundStatusResponse(**result)


@router.post("/start", response_model=PlaygroundStatusResponse)
def playground_start(
    payload: PlaygroundStartRequest,
    db: Session = Depends(get_db),
):
    service = PlaygroundService()
    result = service.start(
        db=db,
        bank_id=payload.bank_id,
        seed_customers=payload.seed_customers,
        tx_per_tick=payload.tx_per_tick,
        aml_alert_rate=payload.aml_alert_rate,
        sanctions_alert_rate=payload.sanctions_alert_rate,
        reset_before_start=payload.reset_before_start,
        actor_id="api-playground",
    )
    return PlaygroundStatusResponse(**result)


@router.post("/stop", response_model=PlaygroundStatusResponse)
def playground_stop(
    bank_id: str = Query(default="demo"),
    db: Session = Depends(get_db),
):
    service = PlaygroundService()
    result = service.stop(db=db, bank_id=bank_id, actor_id="api-playground")
    return PlaygroundStatusResponse(**result)


@router.post("/tick")
def playground_tick(
    payload: PlaygroundTickRequest,
    db: Session = Depends(get_db),
):
    service = PlaygroundService()
    return service.tick(
        db=db,
        bank_id=payload.bank_id,
        count=payload.count,
        run_ingestion_poll=payload.run_ingestion_poll,
        actor_id="api-playground",
    )
