from __future__ import annotations

import uuid

from ..db import LawRepository
from ..schemas import ensure_uuid
from .deterministic import DeterministicMapper
from .explainer import ExplanationEngine, MockLLMExplainer
from .models import (
    CitationResult,
    ControlResult,
    Event,
    MappingResult,
    ObligationResult,
    ProposedRuleMap,
)
from .retrieval import ObligationRetriever, RepositoryObligationRetriever


class LawMappingService:
    def __init__(
        self,
        repository: LawRepository,
        deterministic_mapper: DeterministicMapper | None = None,
        retriever: ObligationRetriever | None = None,
        explainer: ExplanationEngine | None = None,
    ):
        self.repository = repository
        self.deterministic_mapper = deterministic_mapper or DeterministicMapper(repository)
        self.retriever = retriever or RepositoryObligationRetriever(repository)
        self.explainer = explainer or MockLLMExplainer()

    def map_event(self, event: Event) -> MappingResult:
        deterministic = self.deterministic_mapper.map_event(event)
        if deterministic:
            return self._build_deterministic_result(event, deterministic)

        candidates = self.retriever.retrieve(event, top_k=12)
        explained = self.explainer.select_and_explain(event, candidates, min_results=3, max_results=7)

        if not explained:
            return MappingResult(
                event_id=event.event_id,
                mapping_mode="none",
                controls=[],
                obligations=[],
                citations=[],
            )

        # Store suggestions for human approval.
        self.repository.save_proposed_rule_map(
            ProposedRuleMap(
                bank_id=event.bank_id,
                rule_triggered=event.rule_triggered,
                suggested_typology_id=None,
                suggested_control_ids=[],
                candidate_obligation_ids=[ensure_uuid(item.candidate.obligation_id) for item in explained],
                rationale={
                    "event_id": event.event_id,
                    "rule_description": event.rule_description,
                    "model": getattr(self.explainer, "model_name", "mock-llm"),
                    "prompt_version": getattr(self.explainer, "prompt_version", "mock-explain-v1"),
                },
            )
        )

        obligations: list[ObligationResult] = []
        citations: list[CitationResult] = []
        for item in explained:
            candidate = item.candidate
            grounding = candidate.grounding
            obligation_id = ensure_uuid(candidate.obligation_id)

            obligations.append(
                ObligationResult(
                    obligation_id=obligation_id,
                    must_do=candidate.must_do,
                    conditions=candidate.conditions,
                    artifacts_required=candidate.artifacts_required,
                    summary_bullets=candidate.summary_bullets,
                    grounding=grounding,
                )
            )
            citations.append(
                CitationResult(
                    citation=candidate.citation,
                    title=candidate.title,
                    jurisdiction=candidate.jurisdiction,
                    agency=candidate.agency,
                    excerpt=candidate.excerpt,
                    source_url=candidate.source_url,
                    why_relevant=item.why_relevant,
                )
            )

        return MappingResult(
            event_id=event.event_id,
            mapping_mode="fallback",
            controls=[],
            obligations=obligations,
            citations=citations,
        )

    def _build_deterministic_result(self, event: Event, match) -> MappingResult:
        controls = [
            ControlResult(control_id=control.control_id, name=control.name)
            for control in match.controls
        ]

        obligations: list[ObligationResult] = []
        citations: list[CitationResult] = []

        condition_ptr = self._condition_pointer(event)

        for row in match.obligations_with_context:
            obligation_id = ensure_uuid(row["obligation_id"])
            grounding = row.get("grounding") or {}
            grounding_ptr = self._grounding_pointer(grounding)
            why_relevant = (
                f"Deterministic mapping from rule '{event.rule_triggered}'. "
                f"Evidence {condition_ptr}. Pointer {grounding_ptr}."
            )

            obligations.append(
                ObligationResult(
                    obligation_id=obligation_id,
                    must_do=row.get("must_do") or "",
                    conditions=row.get("conditions"),
                    artifacts_required=list(row.get("artifacts_required") or []),
                    summary_bullets=list(row.get("plain_english_summary") or []),
                    grounding=grounding,
                )
            )
            citations.append(
                CitationResult(
                    citation=row.get("citation") or "",
                    title=row.get("title") or "",
                    jurisdiction=row.get("jurisdiction") or "",
                    agency=row.get("agency") or "",
                    excerpt=row.get("chunk_text") or "",
                    source_url=row.get("source_url"),
                    why_relevant=why_relevant,
                )
            )

        return MappingResult(
            event_id=event.event_id,
            mapping_mode="deterministic",
            controls=controls,
            obligations=obligations,
            citations=citations,
        )

    def _condition_pointer(self, event: Event) -> str:
        if not event.conditions_triggered:
            return "condition[rule_description]"
        cond = event.conditions_triggered[0]
        return f"condition[0]={cond.field}:{cond.operator}:{cond.actual}"

    def _grounding_pointer(self, grounding: dict) -> str:
        chunk_id = grounding.get("chunk_id")
        span_start = grounding.get("span_start")
        span_end = grounding.get("span_end")
        if isinstance(span_start, int) and isinstance(span_end, int):
            return f"grounding(chunk_id={chunk_id},span={span_start}-{span_end})"
        return f"grounding(chunk_id={chunk_id},excerpt)"
