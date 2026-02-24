from __future__ import annotations

import re
from typing import Any

from jinja2 import Template
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.db.models import (
    ControlCitationMap,
    LawCitation,
    ProposedRuleMap,
    RegulatoryControlObjective,
    RegulatoryMapping,
    RegulatoryRuleMap,
    RegulatoryTypology,
)


def _choose_best_rule_map(
    rows: list[RegulatoryRuleMap],
    bank_id: str,
) -> RegulatoryRuleMap | None:
    if not rows:
        return None
    exact = [row for row in rows if row.bank_id == bank_id]
    if exact:
        return sorted(exact, key=lambda x: x.updated_at or x.created_at, reverse=True)[0]
    return sorted(rows, key=lambda x: x.updated_at or x.created_at, reverse=True)[0]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _fallback_keyword_tokens(rule_triggered: str, rule_description: str, conditions_triggered: list[dict[str, Any]]) -> list[str]:
    raw = " ".join(
        [
            rule_triggered,
            rule_description,
            " ".join(str(c.get("field") or "") for c in conditions_triggered),
            " ".join(str(c.get("operator") or "") for c in conditions_triggered),
        ]
    ).lower()
    tokens = [token for token in re.findall(r"[a-z0-9_]+", raw) if len(token) > 2]
    return _dedupe(tokens)


def _legacy_mapping(
    db: Session,
    bank_id: str,
    alert_type: str,
    rule_triggered: str,
    evidence_pointers: list[str],
) -> list[dict[str, Any]]:
    mapping = db.scalar(
        select(RegulatoryMapping).where(
            RegulatoryMapping.bank_id.in_([bank_id, "default"]),
            RegulatoryMapping.alert_type == alert_type,
            RegulatoryMapping.rule_triggered == rule_triggered,
        ).order_by(RegulatoryMapping.bank_id.desc())
    )
    if not mapping:
        return []

    pointer = evidence_pointers[0] if evidence_pointers else "NOT PROVIDED"
    why_tpl = Template(mapping.why_relevant_template)
    why = why_tpl.render(rule_triggered=rule_triggered, evidence_pointer=pointer)
    citations: list[dict[str, Any]] = []
    for citation_id in mapping.citation_ids:
        citation = db.get(LawCitation, citation_id)
        if not citation:
            continue
        citations.append(
            {
                "citation_id": citation.citation_id,
                "title": citation.title,
                "jurisdiction": citation.jurisdiction,
                "text_snippet": citation.text_snippet,
                "why_relevant": why,
                "evidence_pointers": evidence_pointers or ["NOT PROVIDED"],
                "mapping_mode": "legacy",
                "controls": [],
                "typology_id": None,
            }
        )
    return citations


def match_citations(
    db: Session,
    bank_id: str,
    alert_type: str,
    rule_triggered: str,
    evidence_pointer: str | None = None,
    evidence_pointers: list[str] | None = None,
    rule_description: str | None = None,
    conditions_triggered: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Deterministic-first mapping with grounded fallback suggestions."""

    pointers = evidence_pointers or ([evidence_pointer] if evidence_pointer else [])
    if not pointers:
        pointers = ["NOT PROVIDED"]
    conds = conditions_triggered or []
    description = rule_description or ""

    rule_rows = db.scalars(
        select(RegulatoryRuleMap).where(
            RegulatoryRuleMap.bank_id.in_([bank_id, "default"]),
            RegulatoryRuleMap.alert_type == alert_type,
            RegulatoryRuleMap.rule_triggered == rule_triggered,
        )
    ).all()
    selected = _choose_best_rule_map(rule_rows, bank_id=bank_id)

    if selected:
        typology = db.get(RegulatoryTypology, selected.typology_id) if selected.typology_id else None
        control_ids = list(selected.control_ids or [])
        if not control_ids and typology:
            control_ids = list(typology.default_control_ids or [])

        control_rows = db.scalars(
            select(RegulatoryControlObjective).where(RegulatoryControlObjective.control_id.in_(control_ids))
        ).all() if control_ids else []
        controls = [{"control_id": row.control_id, "name": row.name} for row in control_rows]

        citation_ids = list(selected.citation_ids or [])
        if control_ids:
            control_maps = db.scalars(
                select(ControlCitationMap)
                .where(ControlCitationMap.control_id.in_(control_ids))
                .order_by(ControlCitationMap.priority.asc(), ControlCitationMap.id.asc())
            ).all()
            for row in control_maps:
                citation_ids.extend([str(c) for c in (row.citation_ids or [])])

        citation_ids = _dedupe(citation_ids)
        citations: list[dict[str, Any]] = []
        for citation_id in citation_ids:
            citation = db.get(LawCitation, citation_id)
            if not citation:
                continue
            why = (
                f"Deterministic mapping for rule '{rule_triggered}'"
                f" linked to controls {[c['control_id'] for c in controls] or ['NOT PROVIDED']}. "
                f"Evidence pointers {', '.join(pointers)}."
            )
            citations.append(
                {
                    "citation_id": citation.citation_id,
                    "title": citation.title,
                    "jurisdiction": citation.jurisdiction,
                    "text_snippet": citation.text_snippet,
                    "why_relevant": why,
                    "evidence_pointers": pointers,
                    "mapping_mode": "deterministic",
                    "controls": controls,
                    "typology_id": selected.typology_id,
                }
            )

        if citations:
            return citations

    # Deterministic maps may be absent in early deployment; fallback is constrained and still evidence-linked.
    tokens = _fallback_keyword_tokens(rule_triggered, description, conds)
    all_citations = db.scalars(select(LawCitation).where(LawCitation.alert_type == alert_type)).all()
    if not all_citations:
        all_citations = db.scalars(select(LawCitation)).all()

    scored: list[tuple[int, LawCitation]] = []
    for citation in all_citations:
        text = f"{citation.title} {citation.text_snippet or ''}".lower()
        score = sum(text.count(token) for token in tokens)
        scored.append((score, citation))
    scored.sort(key=lambda x: x[0], reverse=True)
    picked = [row for row in scored if row[0] > 0][:3]

    candidate_ids = [row[1].citation_id for row in picked]
    if candidate_ids:
        db.add(
            ProposedRuleMap(
                bank_id=bank_id,
                alert_type=alert_type,
                rule_triggered=rule_triggered,
                candidate_citation_ids=candidate_ids,
                rationale={
                    "rule_description": description,
                    "tokens": tokens,
                    "evidence_pointers": pointers,
                    "mode": "keyword-fallback",
                },
                status="PENDING_REVIEW",
            )
        )
        db.commit()

    fallback_citations: list[dict[str, Any]] = []
    for _, citation in picked:
        fallback_citations.append(
            {
                "citation_id": citation.citation_id,
                "title": citation.title,
                "jurisdiction": citation.jurisdiction,
                "text_snippet": citation.text_snippet,
                "why_relevant": (
                    f"Fallback mapping based on rule text matching for '{rule_triggered}'. "
                    f"Evidence pointers {', '.join(pointers)}."
                ),
                "evidence_pointers": pointers,
                "mapping_mode": "fallback",
                "controls": [],
                "typology_id": None,
            }
        )

    if fallback_citations:
        return fallback_citations

    # Last-line compatibility with v1 table.
    return _legacy_mapping(
        db=db,
        bank_id=bank_id,
        alert_type=alert_type,
        rule_triggered=rule_triggered,
        evidence_pointers=pointers,
    )
