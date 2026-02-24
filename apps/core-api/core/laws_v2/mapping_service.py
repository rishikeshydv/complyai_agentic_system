from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.db.models import RegulatoryControlObjective
from core.services.law_matcher import match_citations

from .schemas import CitationResult, ControlResult, Event, MappingResult, ObligationResult


def _normalize_alert_type(event: Event) -> str:
    by_event_type = {
        "AML_ALERT": "AML",
        "SANCTIONS_ALERT": "SANCTIONS",
    }
    if event.event_type in by_event_type:
        return by_event_type[event.event_type]
    metadata_alert_type = (event.metadata or {}).get("alert_type")
    if metadata_alert_type:
        return str(metadata_alert_type).upper()
    return "AML"


def _build_pointers(event: Event) -> list[str]:
    pointers: list[str] = []
    for idx, cond in enumerate(event.conditions_triggered):
        pointers.append(f"ev:cond:{event.rule_triggered}:{idx}:{cond.field}:{cond.operator}")
    if not pointers:
        pointers.append("NOT PROVIDED")
    return pointers


def _build_obligations(
    db: Session,
    event: Event,
    control_ids: list[str],
    evidence_pointers: list[str],
) -> list[ObligationResult]:
    if not control_ids:
        return []

    controls = db.scalars(
        select(RegulatoryControlObjective).where(RegulatoryControlObjective.control_id.in_(control_ids))
    ).all()
    by_id = {row.control_id: row for row in controls}

    obligations: list[ObligationResult] = []
    for control_id in control_ids:
        control = by_id.get(control_id)
        if not control:
            continue
        obligations.append(
            ObligationResult(
                obligation_id=f"obl:{control.control_id}",
                must_do=control.description or "NOT PROVIDED",
                conditions=(
                    f"Rule {event.rule_triggered} triggered with "
                    f"{len(event.conditions_triggered)} condition(s)."
                ),
                artifacts_required=list(control.expected_artifacts or []),
                summary_bullets=[
                    f"{control.name} applies for {event.rule_triggered}.",
                    f"Jurisdiction scope: {control.jurisdiction_scope}.",
                ],
                grounding={
                    "control_id": control.control_id,
                    "evidence_pointers": evidence_pointers,
                },
            )
        )
    return obligations


class LawMappingV2Service:
    """Event mapper that reuses seeded deterministic v2 mappings and fallback logic."""

    def map_event(self, db: Session, event: Event) -> MappingResult:
        alert_type = _normalize_alert_type(event)
        pointers = _build_pointers(event)

        raw = match_citations(
            db=db,
            bank_id=event.bank_id,
            alert_type=alert_type,
            rule_triggered=event.rule_triggered,
            evidence_pointers=pointers,
            rule_description=event.rule_description,
            conditions_triggered=[item.model_dump() for item in event.conditions_triggered],
        )

        if not raw:
            return MappingResult(
                event_id=event.event_id,
                mapping_mode="none",
                controls=[],
                obligations=[],
                citations=[],
            )

        mapping_mode = str(raw[0].get("mapping_mode") or "none")
        if mapping_mode == "legacy":
            mapping_mode = "fallback"
        elif mapping_mode not in {"deterministic", "fallback"}:
            mapping_mode = "none"

        controls_by_id: dict[str, ControlResult] = {}
        control_order: list[str] = []
        citations: list[CitationResult] = []
        for row in raw:
            for control in row.get("controls") or []:
                control_id = str(control.get("control_id") or "").strip()
                if not control_id:
                    continue
                if control_id not in controls_by_id:
                    controls_by_id[control_id] = ControlResult(
                        control_id=control_id,
                        name=str(control.get("name") or "NOT PROVIDED"),
                    )
                    control_order.append(control_id)

            citations.append(
                CitationResult(
                    citation_id=str(row.get("citation_id") or "NOT PROVIDED"),
                    title=str(row.get("title") or "NOT PROVIDED"),
                    jurisdiction=str(row.get("jurisdiction") or "NOT PROVIDED"),
                    text_snippet=row.get("text_snippet"),
                    why_relevant=str(row.get("why_relevant") or "NOT PROVIDED"),
                    evidence_pointers=list(row.get("evidence_pointers") or ["NOT PROVIDED"]),
                    mapping_mode=str(row.get("mapping_mode") or "none"),
                    typology_id=row.get("typology_id"),
                )
            )

        obligations = _build_obligations(
            db=db,
            event=event,
            control_ids=control_order,
            evidence_pointers=pointers,
        )

        return MappingResult(
            event_id=event.event_id,
            mapping_mode=mapping_mode if citations else "none",
            controls=[controls_by_id[cid] for cid in control_order],
            obligations=obligations,
            citations=citations,
        )
