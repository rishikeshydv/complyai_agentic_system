from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol

from ..config import settings
from ..schemas import ObligationCardDraft, RegulatoryChunk


_OBLIGATION_SENTENCE_RE = re.compile(r"(?<=[\.;])\s+|\n+")


@dataclass(frozen=True)
class ExtractionContext:
    jurisdiction: str
    agency: str
    instrument_type: str


class ObligationExtractor(Protocol):
    generator_version: str

    def extract_obligations(
        self,
        chunk: RegulatoryChunk,
        context: ExtractionContext,
    ) -> list[ObligationCardDraft]: ...


class GroundingValidator:
    @staticmethod
    def is_valid(chunk_text: str, grounding: dict[str, Any], expected_chunk_id: str) -> bool:
        if grounding.get("chunk_id") != expected_chunk_id:
            return False

        excerpt = grounding.get("excerpt")
        span_start = grounding.get("span_start")
        span_end = grounding.get("span_end")

        has_excerpt = isinstance(excerpt, str) and bool(excerpt.strip())
        has_span = isinstance(span_start, int) and isinstance(span_end, int)
        if not has_excerpt and not has_span:
            return False

        if has_excerpt and excerpt not in chunk_text:
            return False

        if has_span:
            if span_start < 0 or span_end <= span_start or span_end > len(chunk_text):
                return False
        return True


class MockLLMExtractor:
    """Deterministic-first obligation extractor for local development."""

    generator_version = settings.obligation_generator_version
    model_name = "mock-llm"
    prompt_version = "mock-v1"

    def extract_obligations(
        self,
        chunk: RegulatoryChunk,
        context: ExtractionContext,
    ) -> list[ObligationCardDraft]:
        candidates = self._find_obligation_sentences(chunk.text)
        drafts: list[ObligationCardDraft] = []

        for sentence in candidates[:6]:
            obligation_type = self._classify_obligation(sentence)
            artifacts = self._infer_artifacts(sentence)
            applies_to = self._infer_applies_to(sentence)
            must_do = self._to_must_do(sentence)

            span_start = chunk.text.find(sentence)
            span_end = span_start + len(sentence) if span_start >= 0 else None
            grounding: dict[str, Any] = {"chunk_id": chunk.chunk_id}
            if span_start >= 0 and span_end is not None:
                grounding.update(
                    {
                        "span_start": span_start,
                        "span_end": span_end,
                        "excerpt": sentence,
                    }
                )
            else:
                grounding["excerpt"] = sentence

            summary = self._make_summary(obligation_type, must_do, artifacts)

            draft = ObligationCardDraft(
                chunk_id=chunk.chunk_id,
                applies_to=applies_to,
                jurisdiction=context.jurisdiction,
                agency=context.agency,
                instrument_type=context.instrument_type,
                obligation_type=obligation_type,
                must_do=must_do,
                conditions=self._extract_condition(sentence),
                artifacts_required=artifacts,
                exceptions=None,
                plain_english_summary=summary,
                grounding=grounding,
                review_status="unreviewed",
                confidence=0.72,
                generated_by={
                    "model": self.model_name,
                    "prompt_version": self.prompt_version,
                    "generator_version": self.generator_version,
                    "source_doc_hash": chunk.source_doc_hash,
                },
                source_doc_hash=chunk.source_doc_hash,
            )

            if GroundingValidator.is_valid(chunk.text, draft.grounding, chunk.chunk_id):
                drafts.append(draft)

        return drafts

    def _find_obligation_sentences(self, text: str) -> list[str]:
        sentences = [segment.strip() for segment in _OBLIGATION_SENTENCE_RE.split(text) if segment.strip()]
        obligation_sentences: list[str] = []
        for sentence in sentences:
            s = sentence.lower()
            if any(
                token in s
                for token in [
                    "must ",
                    "shall ",
                    "required",
                    "may not",
                    "must not",
                    "prohibited",
                    "retain",
                    "maintain",
                    "file",
                    "report",
                    "screen",
                ]
            ):
                obligation_sentences.append(sentence)
        return obligation_sentences

    def _classify_obligation(self, sentence: str) -> str:
        s = sentence.lower()
        if any(k in s for k in ["screen", "ofac", "sanction", "blocked"]):
            return "sanctions_screening"
        if any(k in s for k in ["file", "report", "notify", "submit"]):
            return "reporting"
        if any(k in s for k in ["record", "retain", "maintain", "log"]):
            return "recordkeeping"
        if any(k in s for k in ["verify", "identify", "customer due diligence", "kyc", "cip"]):
            return "customer_due_diligence"
        if any(k in s for k in ["monitor", "review", "risk"]):
            return "monitoring"
        return "general_compliance"

    def _infer_artifacts(self, sentence: str) -> list[str]:
        s = sentence.lower()
        artifacts: list[str] = []
        if "sar" in s or "suspicious activity" in s:
            artifacts.append("SAR filing")
        if "ctr" in s or "currency transaction report" in s:
            artifacts.append("CTR filing")
        if any(k in s for k in ["record", "retain", "maintain", "log"]):
            artifacts.append("Retention logs")
        if any(k in s for k in ["policy", "program"]):
            artifacts.append("Policy documentation")
        if any(k in s for k in ["screen", "ofac", "sanction"]):
            artifacts.append("Sanctions screening evidence")
        if not artifacts:
            artifacts.append("Control execution evidence")
        return artifacts

    def _infer_applies_to(self, sentence: str) -> list[str]:
        s = sentence.lower()
        targets: list[str] = []
        if "money services business" in s or "msb" in s:
            targets.append("money_services_business")
        if "bank" in s or "financial institution" in s:
            targets.append("financial_institution")
        if "broker-dealer" in s:
            targets.append("broker_dealer")
        if not targets:
            targets.append("regulated_entity")
        return targets

    def _to_must_do(self, sentence: str) -> str:
        clean = re.sub(r"\s+", " ", sentence).strip()
        return clean[:500]

    def _extract_condition(self, sentence: str) -> str | None:
        s = sentence.lower()
        if "if " in s:
            return sentence[s.index("if ") :].strip()
        if "when " in s:
            return sentence[s.index("when ") :].strip()
        return None

    def _make_summary(self, obligation_type: str, must_do: str, artifacts: list[str]) -> list[str]:
        summary = [
            f"Obligation type: {obligation_type.replace('_', ' ')}.",
            f"Required action: {must_do[:180]}",
            f"Evidence to retain: {', '.join(artifacts[:3])}.",
        ]
        return summary[:6]


class LLMExtractor(MockLLMExtractor):
    """Placeholder for a real LLM-backed extractor.

    This class intentionally falls back to mock behavior unless an external model
    is explicitly wired by the caller.
    """

    model_name = "llm-placeholder"
    prompt_version = "llm-v1"
    generator_version = "llm-obligation-extractor-v1"

    def __init__(self, llm_client: Any | None = None):
        self.llm_client = llm_client

    def extract_obligations(
        self,
        chunk: RegulatoryChunk,
        context: ExtractionContext,
    ) -> list[ObligationCardDraft]:
        if self.llm_client is None:
            return super().extract_obligations(chunk, context)
        # TODO: Add real LLM extraction prompt and response parser. Keep grounded output only.
        return super().extract_obligations(chunk, context)
