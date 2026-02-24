from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.db.models import ControlCitationMap, LawCitation, RegulatoryRuleMap, RegulatoryTypology

from .schemas import SearchResponse, SearchResult


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _tokenize(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9_]+", (text or "").lower()) if len(token) > 2]


def _score_text(tokens: list[str], text: str) -> int:
    hay = (text or "").lower()
    return sum(hay.count(token) for token in tokens)


def _choose_best_rule_map(rows: list[RegulatoryRuleMap], bank_id: str) -> RegulatoryRuleMap | None:
    if not rows:
        return None
    exact = [row for row in rows if row.bank_id == bank_id]
    if exact:
        return sorted(exact, key=lambda x: x.updated_at or x.created_at, reverse=True)[0]
    return sorted(rows, key=lambda x: x.updated_at or x.created_at, reverse=True)[0]


class LawSearchV2Service:
    """Deterministic, local-only law search over curated citation data and v2 mapping context."""

    def _resolve_mapping_context(
        self,
        db: Session,
        *,
        bank_id: str,
        alert_type: str | None,
        rule_triggered: str | None,
    ) -> dict[str, Any]:
        if not rule_triggered:
            return {
                "rule_triggered": None,
                "typology_id": None,
                "control_ids": [],
                "citation_ids": [],
            }

        query = select(RegulatoryRuleMap).where(
            RegulatoryRuleMap.bank_id.in_([bank_id, "default"]),
            RegulatoryRuleMap.rule_triggered == rule_triggered,
        )
        if alert_type:
            query = query.where(RegulatoryRuleMap.alert_type == alert_type)

        rows = db.scalars(query).all()
        selected = _choose_best_rule_map(rows, bank_id=bank_id)
        if not selected:
            return {
                "rule_triggered": rule_triggered,
                "typology_id": None,
                "control_ids": [],
                "citation_ids": [],
            }

        control_ids = list(selected.control_ids or [])
        if not control_ids and selected.typology_id:
            typology = db.get(RegulatoryTypology, selected.typology_id)
            if typology:
                control_ids = list(typology.default_control_ids or [])

        citation_ids = list(selected.citation_ids or [])
        if control_ids:
            control_maps = db.scalars(
                select(ControlCitationMap)
                .where(ControlCitationMap.control_id.in_(control_ids))
                .order_by(ControlCitationMap.priority.asc(), ControlCitationMap.id.asc())
            ).all()
            for row in control_maps:
                citation_ids.extend([str(c) for c in (row.citation_ids or [])])

        return {
            "rule_triggered": selected.rule_triggered,
            "typology_id": selected.typology_id,
            "control_ids": _dedupe([str(c) for c in control_ids]),
            "citation_ids": _dedupe([str(c) for c in citation_ids]),
        }

    def search(
        self,
        db: Session,
        *,
        query: str,
        bank_id: str = "default",
        alert_type: str | None = None,
        jurisdiction: str | None = None,
        rule_triggered: str | None = None,
        top_k: int = 20,
    ) -> SearchResponse:
        tokens = _tokenize(query)
        mapping_context = self._resolve_mapping_context(
            db,
            bank_id=bank_id,
            alert_type=alert_type,
            rule_triggered=rule_triggered,
        )
        mapped_citation_ids = set(mapping_context["citation_ids"])

        q = select(LawCitation)
        if alert_type:
            q = q.where(LawCitation.alert_type == alert_type)
        if jurisdiction:
            q = q.where(LawCitation.jurisdiction == jurisdiction)

        rows = db.scalars(q).all()
        ranked: list[SearchResult] = []
        for row in rows:
            text = " ".join([row.citation_id, row.title, row.text_snippet or ""])
            score = float(_score_text(tokens, text))
            if row.citation_id in mapped_citation_ids:
                score += 4.0

            # If query has no lexical match, keep only context-matched citations.
            if tokens and score <= 0:
                continue
            if not tokens and mapped_citation_ids and row.citation_id not in mapped_citation_ids:
                continue

            ranked.append(
                SearchResult(
                    citation_id=row.citation_id,
                    alert_type=row.alert_type,
                    title=row.title,
                    jurisdiction=row.jurisdiction,
                    text_snippet=row.text_snippet,
                    score=score,
                    mapping_context={
                        "matched_rule_context": row.citation_id in mapped_citation_ids,
                        "rule_triggered": mapping_context["rule_triggered"],
                        "typology_id": mapping_context["typology_id"],
                        "control_ids": mapping_context["control_ids"],
                    },
                )
            )

        ranked.sort(key=lambda x: x.score, reverse=True)
        return SearchResponse(total=len(ranked[:top_k]), results=ranked[:top_k])
