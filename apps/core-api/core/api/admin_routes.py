from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from core.db.models import ProposedRuleMap, RegulatoryMapping, RegulatoryRuleMap
from core.db.session import get_db
from core.schemas.admin import RegulatoryMappingIn, RegulatoryMappingOut, RegulatoryRuleMapIn, RegulatoryRuleMapOut

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.get("/regulatory-mappings", response_model=list[RegulatoryMappingOut])
def get_mappings(
    bank_id: str = "default",
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(RegulatoryMapping).where(RegulatoryMapping.bank_id == bank_id).order_by(RegulatoryMapping.id.asc())
    ).all()
    return [
        RegulatoryMappingOut(
            id=row.id,
            bank_id=row.bank_id,
            alert_type=row.alert_type,
            rule_triggered=row.rule_triggered,
            citation_ids=row.citation_ids,
            why_relevant_template=row.why_relevant_template,
        )
        for row in rows
    ]


@router.put("/regulatory-mappings", response_model=list[RegulatoryMappingOut])
def put_mappings(
    payload: list[RegulatoryMappingIn],
    bank_id: str = "default",
    db: Session = Depends(get_db),
):
    db.execute(delete(RegulatoryMapping).where(RegulatoryMapping.bank_id == bank_id))
    db.commit()

    rows = []
    for item in payload:
        row = RegulatoryMapping(
            bank_id=bank_id,
            alert_type=item.alert_type,
            rule_triggered=item.rule_triggered,
            citation_ids=item.citation_ids,
            why_relevant_template=item.why_relevant_template,
        )
        db.add(row)
        rows.append(row)
    db.commit()

    return [
        RegulatoryMappingOut(
            id=row.id,
            bank_id=row.bank_id,
            alert_type=row.alert_type,
            rule_triggered=row.rule_triggered,
            citation_ids=row.citation_ids,
            why_relevant_template=row.why_relevant_template,
        )
        for row in rows
    ]


@router.get("/rule-maps", response_model=list[RegulatoryRuleMapOut])
def get_rule_maps(
    bank_id: str = "default",
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(RegulatoryRuleMap)
        .where(RegulatoryRuleMap.bank_id == bank_id)
        .order_by(RegulatoryRuleMap.id.asc())
    ).all()
    return [
        RegulatoryRuleMapOut(
            id=row.id,
            bank_id=row.bank_id,
            alert_type=row.alert_type,
            rule_triggered=row.rule_triggered,
            typology_id=row.typology_id,
            control_ids=row.control_ids,
            citation_ids=row.citation_ids,
            confidence=row.confidence,
            version=row.version,
            owner=row.owner,
        )
        for row in rows
    ]


@router.put("/rule-maps", response_model=list[RegulatoryRuleMapOut])
def put_rule_maps(
    payload: list[RegulatoryRuleMapIn],
    bank_id: str = "default",
    db: Session = Depends(get_db),
):
    db.execute(delete(RegulatoryRuleMap).where(RegulatoryRuleMap.bank_id == bank_id))
    db.commit()

    rows = []
    for item in payload:
        row = RegulatoryRuleMap(
            bank_id=bank_id,
            alert_type=item.alert_type,
            rule_triggered=item.rule_triggered,
            typology_id=item.typology_id,
            control_ids=item.control_ids,
            citation_ids=item.citation_ids,
            confidence=item.confidence,
            version=item.version,
            owner=item.owner,
        )
        db.add(row)
        rows.append(row)
    db.commit()

    return [
        RegulatoryRuleMapOut(
            id=row.id,
            bank_id=row.bank_id,
            alert_type=row.alert_type,
            rule_triggered=row.rule_triggered,
            typology_id=row.typology_id,
            control_ids=row.control_ids,
            citation_ids=row.citation_ids,
            confidence=row.confidence,
            version=row.version,
            owner=row.owner,
        )
        for row in rows
    ]


@router.get("/proposed-rule-maps")
def get_proposed_rule_maps(
    bank_id: str = "default",
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = select(ProposedRuleMap).where(ProposedRuleMap.bank_id == bank_id).order_by(ProposedRuleMap.id.desc())
    if status:
        query = query.where(ProposedRuleMap.status == status)
    rows = db.scalars(query).all()
    return [
        {
            "id": row.id,
            "bank_id": row.bank_id,
            "alert_type": row.alert_type,
            "rule_triggered": row.rule_triggered,
            "candidate_citation_ids": row.candidate_citation_ids,
            "rationale": row.rationale,
            "status": row.status,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
        for row in rows
    ]
