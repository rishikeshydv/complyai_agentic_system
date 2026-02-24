from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.db.models import (
    LawCitation,
    ProposedRuleMap,
    RegulatoryControlObjective,
    RegulatoryRuleMap,
    RegulatoryTypology,
)
from core.db.session import get_db
from core.laws_v2.mapping_service import LawMappingV2Service
from core.laws_v2.schemas import Event, MappingResult, SearchResponse
from core.laws_v2.search_service import LawSearchV2Service

router = APIRouter(prefix="/v1/laws-v2", tags=["laws-v2"])


@router.get("/status")
def laws_v2_status(db: Session = Depends(get_db)):
    return {
        "ok": True,
        "counts": {
            "citations": db.scalar(select(func.count()).select_from(LawCitation)) or 0,
            "typologies": db.scalar(select(func.count()).select_from(RegulatoryTypology)) or 0,
            "controls": db.scalar(select(func.count()).select_from(RegulatoryControlObjective)) or 0,
            "rule_maps": db.scalar(select(func.count()).select_from(RegulatoryRuleMap)) or 0,
            "proposed_rule_maps": db.scalar(select(func.count()).select_from(ProposedRuleMap)) or 0,
        },
        "notes": "Search and mapping are deterministic and use curated local law datasets only.",
    }


@router.get("/search", response_model=SearchResponse)
def search_laws_v2(
    q: str = Query(min_length=1),
    bank_id: str = Query(default="default"),
    alert_type: str | None = Query(default=None),
    jurisdiction: str | None = Query(default=None),
    rule_triggered: str | None = Query(default=None),
    top_k: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> SearchResponse:
    service = LawSearchV2Service()
    return service.search(
        db=db,
        query=q,
        bank_id=bank_id,
        alert_type=alert_type,
        jurisdiction=jurisdiction,
        rule_triggered=rule_triggered,
        top_k=top_k,
    )


@router.post("/map-event", response_model=MappingResult)
def map_event_v2(
    event: Event,
    db: Session = Depends(get_db),
) -> MappingResult:
    service = LawMappingV2Service()
    return service.map_event(db=db, event=event)
