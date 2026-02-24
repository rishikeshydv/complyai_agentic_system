from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from core.config import settings
from core.providers.factory import get_provider
from core.services.governance_service import record_llm_invocation
from core.utils.template_loader import render_prompt


class RuleInterpreterAgent:
    prompt_id = "rule_interpreter"
    prompt_template = "rule_interpreter.v1.j2"

    def run(self, db: Session, evidence_graph: dict[str, Any], workflow_run_id: str | None) -> dict[str, Any]:
        provider = get_provider()
        conditions = [n["data"] for n in evidence_graph.get("nodes", []) if n.get("type") == "RULE_CONDITION"]
        default_pointers = [str(c.get("evidence_pointer")) for c in conditions if c.get("evidence_pointer")]
        alert_node = next((n for n in evidence_graph.get("nodes", []) if n.get("type") == "ALERT"), {})

        rendered_prompt = render_prompt(
            self.prompt_template,
            {"evidence_graph_json": json.dumps(evidence_graph, sort_keys=True)},
        )

        context = {
            "rule_triggered": alert_node.get("data", {}).get("rule_triggered", "NOT PROVIDED"),
            "conditions": conditions,
        }

        response = provider.generate_json("rule_interpreter", rendered_prompt, context)

        if "observed_facts" not in response:
            response["observed_facts"] = "NOT PROVIDED"
        if "interpretation" not in response:
            response["interpretation"] = "NOT PROVIDED"
        if not response.get("evidence_pointers"):
            response["evidence_pointers"] = default_pointers or ["NOT PROVIDED"]

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
