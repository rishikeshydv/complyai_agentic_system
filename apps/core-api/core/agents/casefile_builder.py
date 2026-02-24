from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from core.config import settings
from core.providers.factory import get_provider
from core.services.evidence_guard import repair_casefile_evidence
from core.services.governance_service import record_llm_invocation
from core.utils.schema_loader import is_valid
from core.utils.template_loader import render_prompt


def _safe(value: Any) -> Any:
    if value is None or value == "":
        return "NOT PROVIDED"
    return value


class CaseFileBuilderAgent:
    prompt_id = "casefile_summary"
    prompt_template = "casefile_summary.v1.j2"

    def run(
        self,
        db: Session,
        evidence_graph: dict[str, Any],
        trigger_explanation: dict[str, Any],
        workflow_run_id: str | None,
    ) -> dict[str, Any]:
        provider = get_provider()

        alert_node = next((n for n in evidence_graph["nodes"] if n["type"] == "ALERT"), {"data": {}})
        alert_data = alert_node.get("data", {})

        condition_nodes = [n for n in evidence_graph["nodes"] if n["type"] == "RULE_CONDITION"]
        customer_node = next((n for n in evidence_graph["nodes"] if n["type"] == "CUSTOMER"), {"data": {}})
        tx_node = next((n for n in evidence_graph["nodes"] if n["type"] == "TRANSACTION"), {"data": {}})
        agg_node = next((n for n in evidence_graph["nodes"] if n["type"] == "AGGREGATE"), {"data": {}})
        law_nodes = [n for n in evidence_graph["nodes"] if n["type"] == "LAW_CITATION"]

        rule_rows = []
        pointers = []
        for cond in condition_nodes:
            actual = cond["data"].get("actual")
            threshold = cond["data"].get("threshold")
            satisfied = False
            if isinstance(actual, (int, float)) and isinstance(threshold, (int, float)):
                satisfied = actual >= threshold
            row = {
                "field": _safe(cond["data"].get("field")),
                "operator": _safe(cond["data"].get("operator")),
                "threshold": _safe(threshold),
                "actual": _safe(actual),
                "window_days": cond["data"].get("window_days"),
                "satisfied": satisfied,
                "evidence_pointer": cond.get("evidence_pointer", "NOT PROVIDED"),
            }
            pointers.append(row["evidence_pointer"])
            rule_rows.append(row)

        customer_snapshot = customer_node.get("data", {}).get("snapshot", {})
        tx_snapshot = tx_node.get("data", {}).get("snapshot", {})
        agg_data = agg_node.get("data", {})
        agg_values = agg_data.get("aggregates", {}) if isinstance(agg_data, dict) else {}
        linked = agg_data.get("linked_transactions", []) if isinstance(agg_data, dict) else []

        rendered_prompt = render_prompt(
            self.prompt_template,
            {
                "evidence_graph_json": json.dumps(evidence_graph, sort_keys=True),
                "trigger_explanation_json": json.dumps(trigger_explanation, sort_keys=True),
            },
        )

        summary_context = {
            "alert_type": alert_data.get("alert_type", "NOT PROVIDED"),
            "rule_triggered": alert_data.get("rule_triggered", "NOT PROVIDED"),
            "customer_risk_rating": customer_snapshot.get("kyc_risk_rating", "NOT PROVIDED"),
            "evidence_pointers": pointers,
        }
        summary = provider.generate_json("casefile_summary", rendered_prompt, summary_context)

        if not summary.get("bullets"):
            summary["bullets"] = ["NOT PROVIDED"]
        if not summary.get("evidence_pointers"):
            summary["evidence_pointers"] = ["NOT PROVIDED"]

        casefile: dict[str, Any] = {
            "schema_version": settings.casefile_schema_version,
            "prompt_version": settings.prompt_version,
            "model_provider": provider.provider_name,
            "model_name": provider.model_name,
            "evidence_hash": evidence_graph["evidence_hash"],
            "header": {
                "alert_id": evidence_graph["alert_id"],
                "alert_type": alert_data.get("alert_type", "NOT PROVIDED"),
                "status": "READY_FOR_REVIEW",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "customer_id": alert_data.get("customer_id"),
                "transaction_id": alert_data.get("transaction_id"),
                "source_system": alert_data.get("alert_metadata", {}).get("source_system"),
            },
            "executive_summary": {
                "bullets": summary["bullets"],
                "recommended_disposition": summary.get("recommended_disposition", "REVIEW"),
                "confidence": float(summary.get("confidence", 0.5)),
                "evidence_pointers": summary["evidence_pointers"],
            },
            "trigger_explanation": trigger_explanation,
            "rule_evaluation_table": {"rows": rule_rows},
            "customer_context": {
                "summary": (
                    f"Customer type is {_safe(customer_snapshot.get('customer_type'))} in segment {_safe(customer_snapshot.get('segment'))}. "
                    f"KYC risk rating is {_safe(customer_snapshot.get('kyc_risk_rating'))}; prior alerts (12m) are {_safe(customer_snapshot.get('prior_alerts_12m'))} "
                    f"and prior SARs (12m) are {_safe(customer_snapshot.get('prior_sar_12m'))}."
                ),
                "key_facts": [
                    {"label": "Customer Type", "value": _safe(customer_snapshot.get("customer_type")), "evidence_pointer": customer_node.get("evidence_pointer", "NOT PROVIDED")},
                    {"label": "Segment", "value": _safe(customer_snapshot.get("segment")), "evidence_pointer": customer_node.get("evidence_pointer", "NOT PROVIDED")},
                    {"label": "KYC Risk Rating", "value": _safe(customer_snapshot.get("kyc_risk_rating")), "evidence_pointer": customer_node.get("evidence_pointer", "NOT PROVIDED")},
                    {"label": "EDD", "value": _safe(customer_snapshot.get("edd")), "evidence_pointer": customer_node.get("evidence_pointer", "NOT PROVIDED")},
                ],
            },
            "transaction_evidence": {
                "summary": (
                    f"Transaction type {_safe(tx_snapshot.get('type'))} via {_safe(tx_snapshot.get('channel'))} at {_safe(tx_snapshot.get('occurred_at'))} with descriptor {_safe(tx_snapshot.get('description'))}. "
                    f"Aggregates used include keys: {', '.join(sorted(agg_values.keys())) if agg_values else 'NOT PROVIDED'}."
                ),
                "key_transactions": [
                    {
                        "transaction_id": _safe(tx_snapshot.get("transaction_id")),
                        "description": (
                            f"Primary transaction type={_safe(tx_snapshot.get('type'))}, amount={_safe(tx_snapshot.get('amount'))}, "
                            f"channel={_safe(tx_snapshot.get('channel'))}, occurred_at={_safe(tx_snapshot.get('occurred_at'))}"
                        ),
                        "evidence_pointer": tx_node.get("evidence_pointer", "NOT PROVIDED"),
                    }
                ]
                + [
                    {
                        "transaction_id": _safe(item.get("transaction_id")),
                        "description": _safe(item.get("description")),
                        "evidence_pointer": agg_node.get("evidence_pointer", "NOT PROVIDED"),
                    }
                    for item in linked
                ],
                "aggregates": [
                    {"label": k, "value": v, "evidence_pointer": agg_node.get("evidence_pointer", "NOT PROVIDED")}
                    for k, v in agg_values.items()
                ]
                or [{"label": "NOT PROVIDED", "value": "NOT PROVIDED", "evidence_pointer": "NOT PROVIDED"}],
            },
            "regulatory_traceability": {
                "citations": [
                    {
                        "citation_id": n["data"].get("citation_id", "NOT PROVIDED"),
                        "title": n["data"].get("title", "NOT PROVIDED"),
                        "jurisdiction": n["data"].get("jurisdiction", "NOT PROVIDED"),
                        "text_snippet": n["data"].get("text_snippet"),
                        "why_relevant": n["data"].get("why_relevant", "NOT PROVIDED"),
                        "evidence_pointers": n["data"].get("evidence_pointers", ["NOT PROVIDED"]),
                    }
                    for n in law_nodes
                ],
            },
            "timeline_and_audit": {"events": []},
            "sar_draft": {
                "required": False,
                "narrative_draft": "NOT PROVIDED",
                "fields": {
                    "subject_customer_id": _safe(alert_data.get("customer_id")),
                    "activity_date": _safe(tx_snapshot.get("occurred_at")),
                    "activity_amount": _safe(tx_snapshot.get("amount")),
                    "activity_currency": _safe(tx_snapshot.get("currency")),
                    "rule_triggered": _safe(alert_data.get("rule_triggered")),
                },
                "evidence_pointers": pointers or ["NOT PROVIDED"],
            },
            "export_bundle": {
                "version": "1.0",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "export_id": "NOT PROVIDED",
                "source_payload_hash": evidence_graph.get("source_payload_hash", "NOT PROVIDED"),
                "evidence_hash": evidence_graph["evidence_hash"],
                "casefile_hash": "NOT PROVIDED",
            },
        }

        casefile = repair_casefile_evidence(casefile=casefile, evidence_graph=evidence_graph)

        valid, _ = is_valid("casefile.schema.json", casefile)
        if not valid:
            casefile = self._repair_casefile(casefile)

        record_llm_invocation(
            db=db,
            workflow_run_id=workflow_run_id,
            case_id=None,
            prompt_id=self.prompt_id,
            version=settings.prompt_version,
            rendered_prompt=rendered_prompt,
            model_provider=provider.provider_name,
            model_name=provider.model_name,
            request_payload=summary_context,
            response_payload=summary,
        )
        return casefile

    def _repair_casefile(self, casefile: dict[str, Any]) -> dict[str, Any]:
        casefile.setdefault("executive_summary", {})
        casefile["executive_summary"].setdefault("bullets", ["NOT PROVIDED"])
        casefile["executive_summary"].setdefault("recommended_disposition", "REVIEW")
        casefile["executive_summary"].setdefault("confidence", 0.5)
        casefile["executive_summary"].setdefault("evidence_pointers", ["NOT PROVIDED"])
        casefile.setdefault("trigger_explanation", {})
        casefile["trigger_explanation"].setdefault("observed_facts", "NOT PROVIDED")
        casefile["trigger_explanation"].setdefault("interpretation", "NOT PROVIDED")
        casefile["trigger_explanation"].setdefault("evidence_pointers", ["NOT PROVIDED"])
        casefile.setdefault("regulatory_traceability", {}).setdefault("citations", [])
        casefile.setdefault("export_bundle", {}).setdefault("source_payload_hash", "NOT PROVIDED")
        return casefile
