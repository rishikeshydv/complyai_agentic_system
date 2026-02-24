from __future__ import annotations

from typing import Any

from core.providers.base import LLMProvider


class MockLLMProvider(LLMProvider):
    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-llm-v1"

    def generate_json(self, task: str, rendered_prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        if task == "rule_interpreter":
            rule = context.get("rule_triggered", "NOT PROVIDED")
            conditions = context.get("conditions", [])
            facts = []
            pointers = []
            for idx, cond in enumerate(conditions):
                threshold = cond.get("threshold", "NOT PROVIDED")
                actual = cond.get("actual", "NOT PROVIDED")
                field = cond.get("field", "NOT PROVIDED")
                pointer = cond.get("evidence_pointer", f"ev:cond:{rule}:{idx}")
                pointers.append(pointer)
                facts.append(f"{field} actual={actual} threshold={threshold}")

            observed = "; ".join(facts) if facts else "NOT PROVIDED"
            interpretation = (
                f"Bank rule {rule} flagged based on {len(conditions)} observed condition(s). "
                f"[evidence: {', '.join(pointers or ['NOT PROVIDED'])}]"
                if conditions
                else "NOT PROVIDED"
            )
            return {
                "observed_facts": observed,
                "interpretation": interpretation,
                "evidence_pointers": pointers or ["NOT PROVIDED"],
            }

        if task == "casefile_summary":
            alert_type = context.get("alert_type", "NOT PROVIDED")
            rule = context.get("rule_triggered", "NOT PROVIDED")
            pointers = context.get("evidence_pointers", [])
            risk = context.get("customer_risk_rating", "NOT PROVIDED")
            disposition = "ESCALATE" if alert_type in {"AML", "SANCTIONS"} else "REVIEW"
            confidence = 0.82 if alert_type == "SANCTIONS" else 0.74
            return {
                "bullets": [
                    f"Rule {rule} triggered using deterministic threshold checks. [evidence: {', '.join(pointers or ['NOT PROVIDED'])}]",
                    f"Customer risk rating is {risk}. [evidence: {', '.join(pointers or ['NOT PROVIDED'])}]",
                    f"Recommended disposition is {disposition} based on evidence only. [evidence: {', '.join(pointers or ['NOT PROVIDED'])}]",
                ],
                "recommended_disposition": disposition,
                "confidence": confidence,
                "evidence_pointers": pointers or ["NOT PROVIDED"],
            }

        if task == "sar_copilot":
            alert_id = context.get("alert_id", "NOT PROVIDED")
            rule = context.get("rule_triggered", "NOT PROVIDED")
            pointers = context.get("evidence_pointers", [])
            fields = context.get("sar_fields", {})
            return {
                "required": True,
                "narrative_draft": (
                    f"Alert {alert_id} triggered {rule} based on observed evidence. "
                    f"This draft is evidence-grounded and requires analyst review before filing. [evidence: {', '.join(pointers or ['NOT PROVIDED'])}]"
                ),
                "fields": fields,
                "evidence_pointers": pointers or ["NOT PROVIDED"],
            }

        return {"result": "NOT PROVIDED"}
