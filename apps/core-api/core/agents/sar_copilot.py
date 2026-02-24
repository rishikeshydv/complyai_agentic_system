from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from core.config import settings
from core.providers.factory import get_provider
from core.services.governance_service import record_llm_invocation
from core.utils.template_loader import render_prompt


class SARCopilotAgent:
    prompt_id = "sar_copilot"
    prompt_template = "sar_copilot.v1.j2"

    def run(
        self,
        db: Session,
        evidence_graph: dict[str, Any],
        casefile: dict[str, Any],
        workflow_run_id: str | None,
    ) -> dict[str, Any]:
        provider = get_provider()

        alert_node = next((n for n in evidence_graph["nodes"] if n["type"] == "ALERT"), {"data": {}})
        tx_node = next((n for n in evidence_graph["nodes"] if n["type"] == "TRANSACTION"), {"data": {}})
        cond_nodes = [n for n in evidence_graph["nodes"] if n["type"] == "RULE_CONDITION"]

        pointers = [n.get("evidence_pointer", "NOT PROVIDED") for n in cond_nodes] or [
            alert_node.get("evidence_pointer", "NOT PROVIDED")
        ]

        context = {
            "alert_id": evidence_graph.get("alert_id", "NOT PROVIDED"),
            "rule_triggered": alert_node.get("data", {}).get("rule_triggered", "NOT PROVIDED"),
            "evidence_pointers": pointers,
            "sar_fields": {
                "subject_customer_id": alert_node.get("data", {}).get("customer_id", "NOT PROVIDED") or "NOT PROVIDED",
                "activity_date": tx_node.get("data", {}).get("snapshot", {}).get("occurred_at", "NOT PROVIDED")
                or "NOT PROVIDED",
                "activity_amount": tx_node.get("data", {}).get("snapshot", {}).get("amount", "NOT PROVIDED")
                or "NOT PROVIDED",
                "activity_currency": tx_node.get("data", {}).get("snapshot", {}).get("currency", "NOT PROVIDED")
                or "NOT PROVIDED",
                "rule_triggered": alert_node.get("data", {}).get("rule_triggered", "NOT PROVIDED") or "NOT PROVIDED",
            },
        }

        rendered_prompt = render_prompt(
            self.prompt_template,
            {
                "evidence_graph_json": json.dumps(evidence_graph, sort_keys=True),
                "casefile_json": json.dumps(casefile, sort_keys=True),
            },
        )
        response = provider.generate_json("sar_copilot", rendered_prompt, context)

        response.setdefault("required", True)
        response.setdefault("narrative_draft", "NOT PROVIDED")
        response.setdefault("fields", context["sar_fields"])
        response.setdefault("evidence_pointers", pointers)

        record_llm_invocation(
            db=db,
            workflow_run_id=workflow_run_id,
            case_id=None,
            prompt_id=self.prompt_id,
            version=settings.prompt_version,
            rendered_prompt=rendered_prompt,
            model_provider=provider.provider_name,
            model_name=provider.model_name,
            request_payload=context,
            response_payload=response,
        )

        return response
