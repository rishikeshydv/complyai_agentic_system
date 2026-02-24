from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol

from .models import Event
from .retrieval import RetrievalCandidate


@dataclass(frozen=True)
class ExplainedCandidate:
    candidate: RetrievalCandidate
    why_relevant: str


class ExplanationEngine(Protocol):
    def select_and_explain(
        self,
        event: Event,
        candidates: list[RetrievalCandidate],
        min_results: int = 3,
        max_results: int = 7,
    ) -> list[ExplainedCandidate]: ...


class MockLLMExplainer:
    """Mock rerank + explainer with strict grounding validation."""

    model_name = "mock-llm"
    prompt_version = "mock-explain-v1"

    def select_and_explain(
        self,
        event: Event,
        candidates: list[RetrievalCandidate],
        min_results: int = 3,
        max_results: int = 7,
    ) -> list[ExplainedCandidate]:
        if not candidates:
            return []

        scored = sorted(candidates, key=lambda candidate: self._score(event, candidate), reverse=True)
        target_n = max(min_results, min(max_results, len(scored)))

        explained: list[ExplainedCandidate] = []
        for candidate in scored:
            if len(explained) >= target_n:
                break
            if not self._candidate_grounding_valid(candidate):
                continue
            why = self._build_why(event, candidate)
            if not self._why_grounded(why):
                continue
            explained.append(ExplainedCandidate(candidate=candidate, why_relevant=why))

        return explained

    def _score(self, event: Event, candidate: RetrievalCandidate) -> int:
        text = " ".join(
            [
                event.rule_description.lower(),
                " ".join(f"{c.field} {c.operator}" for c in event.conditions_triggered),
            ]
        )
        candidate_text = " ".join(
            [
                candidate.must_do.lower(),
                (candidate.conditions or "").lower(),
                " ".join(s.lower() for s in candidate.summary_bullets),
                candidate.excerpt.lower(),
            ]
        )
        score = 0
        for token in re.findall(r"[a-z0-9_]+", text):
            if len(token) <= 2:
                continue
            score += candidate_text.count(token)
        return score

    def _candidate_grounding_valid(self, candidate: RetrievalCandidate) -> bool:
        grounding = candidate.grounding or {}
        if grounding.get("chunk_id") != candidate.chunk_id:
            return False

        excerpt = grounding.get("excerpt")
        span_start = grounding.get("span_start")
        span_end = grounding.get("span_end")

        has_excerpt = isinstance(excerpt, str) and bool(excerpt)
        has_span = isinstance(span_start, int) and isinstance(span_end, int)

        if not has_excerpt and not has_span:
            return False

        if has_excerpt and excerpt not in candidate.excerpt:
            return False

        if has_span:
            if span_start < 0 or span_end <= span_start:
                return False
            if candidate.excerpt and span_end > len(candidate.excerpt):
                return False
        return True

    def _build_why(self, event: Event, candidate: RetrievalCandidate) -> str:
        if event.conditions_triggered:
            cond = event.conditions_triggered[0]
            condition_ptr = f"condition[0]={cond.field}:{cond.operator}:{cond.actual}"
        else:
            condition_ptr = "condition[rule_description]"

        grounding = candidate.grounding
        chunk_id = grounding.get("chunk_id")
        span_start = grounding.get("span_start")
        span_end = grounding.get("span_end")
        if isinstance(span_start, int) and isinstance(span_end, int):
            grounding_ptr = f"grounding(chunk_id={chunk_id},span={span_start}-{span_end})"
        else:
            grounding_ptr = f"grounding(chunk_id={chunk_id},excerpt)"

        return (
            f"Evidence {condition_ptr} aligns with obligation '{candidate.must_do[:120]}'. "
            f"Pointer {grounding_ptr}."
        )

    def _why_grounded(self, why: str) -> bool:
        has_condition_ptr = "condition[" in why
        has_grounding_ptr = "grounding(chunk_id=" in why
        return has_condition_ptr and has_grounding_ptr


class LLMExplainer(MockLLMExplainer):
    model_name = "llm-placeholder"
    prompt_version = "llm-explain-v1"

    def __init__(self, llm_client: Any | None = None):
        self.llm_client = llm_client

    def select_and_explain(
        self,
        event: Event,
        candidates: list[RetrievalCandidate],
        min_results: int = 3,
        max_results: int = 7,
    ) -> list[ExplainedCandidate]:
        if self.llm_client is None:
            return super().select_and_explain(event, candidates, min_results=min_results, max_results=max_results)
        # TODO: Add real LLM reranker/explainer; reject any ungrounded outputs.
        return super().select_and_explain(event, candidates, min_results=min_results, max_results=max_results)
