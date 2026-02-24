from __future__ import annotations

from typing import Any


def _allowed_pointers(evidence_graph: dict[str, Any]) -> set[str]:
    pointers = {
        str(node.get("evidence_pointer"))
        for node in evidence_graph.get("nodes", [])
        if node.get("evidence_pointer")
    }
    pointers.add("NOT PROVIDED")
    return pointers


def _normalize_pointer(value: Any, allowed: set[str]) -> str:
    pointer = str(value or "NOT PROVIDED")
    if pointer in allowed:
        return pointer
    return "NOT PROVIDED"


def _normalize_pointer_list(values: Any, allowed: set[str]) -> list[str]:
    if not isinstance(values, list):
        return ["NOT PROVIDED"]
    normalized = [_normalize_pointer(value, allowed) for value in values]
    normalized = [value for value in normalized if value]
    return normalized or ["NOT PROVIDED"]


def _attach_pointer_hint(text: Any, pointers: list[str]) -> str:
    content = str(text or "NOT PROVIDED")
    if content == "NOT PROVIDED":
        return content
    if "evidence:" in content.lower() or "ev:" in content:
        return content
    ptrs = ", ".join(pointers or ["NOT PROVIDED"])
    return f"{content} [evidence: {ptrs}]"


def repair_casefile_evidence(casefile: dict[str, Any], evidence_graph: dict[str, Any]) -> dict[str, Any]:
    """Normalize pointers and ensure generated language remains evidence-linked."""

    allowed = _allowed_pointers(evidence_graph)

    summary = casefile.setdefault("executive_summary", {})
    summary["evidence_pointers"] = _normalize_pointer_list(summary.get("evidence_pointers"), allowed)
    bullets = summary.get("bullets")
    if not isinstance(bullets, list) or not bullets:
        summary["bullets"] = ["NOT PROVIDED"]
    else:
        summary["bullets"] = [_attach_pointer_hint(item, summary["evidence_pointers"]) for item in bullets]

    trigger = casefile.setdefault("trigger_explanation", {})
    trigger["evidence_pointers"] = _normalize_pointer_list(trigger.get("evidence_pointers"), allowed)
    trigger["observed_facts"] = _attach_pointer_hint(trigger.get("observed_facts"), trigger["evidence_pointers"])
    trigger["interpretation"] = _attach_pointer_hint(trigger.get("interpretation"), trigger["evidence_pointers"])

    rows = casefile.setdefault("rule_evaluation_table", {}).setdefault("rows", [])
    for row in rows:
        row["evidence_pointer"] = _normalize_pointer(row.get("evidence_pointer"), allowed)

    for fact in casefile.setdefault("customer_context", {}).setdefault("key_facts", []):
        fact["evidence_pointer"] = _normalize_pointer(fact.get("evidence_pointer"), allowed)
    for tx in casefile.setdefault("transaction_evidence", {}).setdefault("key_transactions", []):
        tx["evidence_pointer"] = _normalize_pointer(tx.get("evidence_pointer"), allowed)
    for agg in casefile.setdefault("transaction_evidence", {}).setdefault("aggregates", []):
        agg["evidence_pointer"] = _normalize_pointer(agg.get("evidence_pointer"), allowed)

    citations = casefile.setdefault("regulatory_traceability", {}).setdefault("citations", [])
    for citation in citations:
        citation["evidence_pointers"] = _normalize_pointer_list(citation.get("evidence_pointers"), allowed)
        citation["why_relevant"] = _attach_pointer_hint(citation.get("why_relevant"), citation["evidence_pointers"])

    sar = casefile.setdefault("sar_draft", {})
    sar["evidence_pointers"] = _normalize_pointer_list(sar.get("evidence_pointers"), allowed)
    sar["narrative_draft"] = _attach_pointer_hint(sar.get("narrative_draft"), sar["evidence_pointers"])

    export = casefile.setdefault("export_bundle", {})
    export.setdefault("source_payload_hash", evidence_graph.get("source_payload_hash", "NOT PROVIDED"))
    export.setdefault("evidence_hash", evidence_graph.get("evidence_hash", "NOT PROVIDED"))

    return casefile

