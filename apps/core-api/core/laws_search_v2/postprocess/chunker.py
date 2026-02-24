from __future__ import annotations

import re
from dataclasses import dataclass

from ..config import settings
from ..schemas import (
    RegulatoryChunk,
    RegulatoryDocumentRecord,
    chunk_hash,
    make_chunk_id,
    stable_node_id,
    utcnow,
)


_HEADING_RE = re.compile(
    r"^(section|sec\.|article|chapter|part|subpart|appendix|\d+(\.\d+)*\.?|[A-Z]\.)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ChunkerConfig:
    min_chars: int = settings.chunk_min_chars
    max_chars: int = settings.chunk_max_chars


class DeterministicChunker:
    def __init__(self, config: ChunkerConfig | None = None):
        self.config = config or ChunkerConfig()

    def chunk_document(self, doc: RegulatoryDocumentRecord) -> list[RegulatoryChunk]:
        text = (doc.body_text or "").replace("\r\n", "\n").strip()
        if not text:
            return []

        node_id = stable_node_id(doc.citation, doc.version_id, doc.doc_family_id)
        units = self._to_units(text)
        chunk_payloads = self._build_chunk_payloads(units)
        chunk_payloads = self._merge_small_chunks(chunk_payloads)

        created_at = utcnow()
        chunks: list[RegulatoryChunk] = []
        search_start = 0
        for idx, payload in enumerate(chunk_payloads):
            chunk_text = payload["text"].strip()
            if not chunk_text:
                continue
            start = text.find(chunk_text, search_start)
            if start == -1:
                start = None
                end = None
            else:
                end = start + len(chunk_text)
                search_start = end

            c_hash = chunk_hash(chunk_text)
            chunks.append(
                RegulatoryChunk(
                    chunk_id=make_chunk_id(node_id=node_id, chunk_index=idx, content_hash=doc.content_hash),
                    doc_id=doc.id,
                    node_id=node_id,
                    citation=doc.citation,
                    chunk_index=idx,
                    heading_path=payload.get("heading_path"),
                    text=chunk_text,
                    span_start=start,
                    span_end=end,
                    chunk_hash=c_hash,
                    source_doc_hash=doc.content_hash,
                    created_at=created_at,
                    updated_at=created_at,
                )
            )
        return chunks

    def _to_units(self, text: str) -> list[dict[str, str]]:
        units: list[dict[str, str]] = []
        paragraph_lines: list[str] = []

        def flush_paragraph() -> None:
            if not paragraph_lines:
                return
            paragraph = " ".join(line.strip() for line in paragraph_lines if line.strip()).strip()
            if paragraph:
                if self._is_heading(paragraph):
                    units.append({"kind": "heading", "text": paragraph})
                else:
                    units.append({"kind": "text", "text": paragraph})
            paragraph_lines.clear()

        for raw_line in text.split("\n"):
            line = raw_line.strip()
            if not line:
                flush_paragraph()
                continue
            paragraph_lines.append(line)
        flush_paragraph()
        return units

    def _is_heading(self, paragraph: str) -> bool:
        if len(paragraph) > 140:
            return False
        if _HEADING_RE.search(paragraph):
            return True
        alpha = re.sub(r"[^A-Za-z]", "", paragraph)
        if alpha and alpha.isupper() and len(alpha) >= 6:
            return True
        return paragraph.endswith(":") and len(paragraph) < 100

    def _build_chunk_payloads(self, units: list[dict[str, str]]) -> list[dict[str, str | None]]:
        payloads: list[dict[str, str | None]] = []
        heading_stack: list[str] = []
        current_parts: list[str] = []
        current_heading: str | None = None

        def flush_current() -> None:
            if not current_parts:
                return
            payloads.append(
                {
                    "heading_path": current_heading,
                    "text": "\n\n".join(part for part in current_parts if part.strip()),
                }
            )
            current_parts.clear()

        for unit in units:
            kind = unit["kind"]
            value = unit["text"].strip()
            if not value:
                continue

            if kind == "heading":
                heading_stack = self._update_heading_stack(heading_stack, value)
                current_heading = " > ".join(heading_stack)
                continue

            candidate = value if not current_parts else "\n\n".join([*current_parts, value])
            if len(candidate) <= self.config.max_chars or len("\n\n".join(current_parts)) < self.config.min_chars:
                current_parts.append(value)
            else:
                flush_current()
                current_parts.append(value)

        flush_current()
        return payloads

    def _merge_small_chunks(self, payloads: list[dict[str, str | None]]) -> list[dict[str, str | None]]:
        if not payloads:
            return []
        merged: list[dict[str, str | None]] = []
        for payload in payloads:
            text = (payload["text"] or "").strip()
            if not text:
                continue
            if not merged:
                merged.append(payload)
                continue
            if len(text) < self.config.min_chars:
                prev = merged[-1]
                prev_text = (prev["text"] or "").strip()
                combined = f"{prev_text}\n\n{text}".strip()
                if len(combined) <= int(self.config.max_chars * 1.25):
                    merged[-1] = {
                        "heading_path": prev.get("heading_path") or payload.get("heading_path"),
                        "text": combined,
                    }
                    continue
            merged.append(payload)
        return merged

    def _update_heading_stack(self, stack: list[str], heading: str) -> list[str]:
        level = self._infer_heading_level(heading)
        if level <= 1:
            return [heading]
        trimmed = stack[: max(level - 1, 0)]
        trimmed.append(heading)
        return trimmed

    def _infer_heading_level(self, heading: str) -> int:
        match = re.match(r"^(\d+(?:\.\d+)*)", heading)
        if match:
            return match.group(1).count(".") + 1
        if re.match(r"^[A-Z]\.\s", heading):
            return 2
        if heading.lower().startswith(("section", "article", "chapter", "part", "subpart")):
            return 1
        return 1
