from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from core.services.connector_client import ConnectorClient
from core.services.law_matcher import match_citations
from core.utils.hashing import sha256_json
from core.utils.schema_loader import validate_json


class EvidenceService:
    def __init__(self, connector_client: ConnectorClient | None = None):
        self.connector = connector_client or ConnectorClient()

    @staticmethod
    def _connector_call(method, *args, bank_id: str):
        try:
            return method(*args, bank_id=bank_id)
        except TypeError:
            return method(*args)

    def build_evidence_graph(self, db: Session, alert_id: str, bank_id: str) -> dict[str, Any]:
        alert = self._connector_call(self.connector.fetch_alert, alert_id, bank_id=bank_id)
        validate_json("connector_alert.schema.json", alert)
        conditions = alert.get("rule_evaluation", {}).get("conditions_triggered", [])
        rule_triggered = alert.get("rule_triggered", "NOT PROVIDED")
        customer_id = alert.get("customer_id")
        transaction_id = alert.get("transaction_id")

        missing: list[dict[str, str]] = []

        customer_snapshot: dict[str, Any] | None = None
        if customer_id:
            customer_payload = self._connector_call(self.connector.fetch_customer, customer_id, bank_id=bank_id)
            validate_json("connector_customer.schema.json", customer_payload)
            customer_snapshot = customer_payload.get("snapshot", {})
        else:
            missing.append({"field": "customer_id", "reason": "NOT PROVIDED"})

        transaction_snapshot: dict[str, Any] | None = None
        if transaction_id:
            tx_payload = self._connector_call(self.connector.fetch_transaction, transaction_id, bank_id=bank_id)
            validate_json("connector_transaction.schema.json", tx_payload)
            transaction_snapshot = tx_payload.get("snapshot", {})
        else:
            missing.append({"field": "transaction_id", "reason": "NOT PROVIDED"})

        window_days = None
        if conditions:
            nums = [c.get("window_days") for c in conditions if c.get("window_days") is not None]
            if nums:
                window_days = max(nums)

        aggregate_payload: dict[str, Any] = {"aggregates": {}, "linked_transactions": []}
        if customer_id and rule_triggered and rule_triggered != "NOT PROVIDED":
            try:
                aggregate_payload = self._connector_call(
                    self.connector.fetch_aggregates,
                    customer_id,
                    rule_triggered,
                    window_days,
                    bank_id=bank_id,
                )
                validate_json("connector_aggregates.schema.json", aggregate_payload)
            except Exception:
                missing.append({"field": "aggregates", "reason": "NOT PROVIDED"})
        else:
            missing.append({"field": "aggregates", "reason": "NOT PROVIDED"})

        sanctions_hits: list[dict[str, Any]] = []
        if alert.get("alert_type") == "SANCTIONS":
            try:
                sanctions_payload = self._connector_call(self.connector.fetch_sanctions_hits, alert_id, bank_id=bank_id)
                validate_json("connector_sanctions_hit.schema.json", sanctions_payload)
                sanctions_hits = sanctions_payload.get("hits", [])
            except Exception:
                missing.append({"field": "sanctions_hits", "reason": "NOT PROVIDED"})

        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, str]] = []

        alert_node_id = f"ev:alert:{alert_id}"
        nodes.append({"id": alert_node_id, "type": "ALERT", "evidence_pointer": alert_node_id, "data": alert})

        cond_pointers: list[str] = []
        for idx, cond in enumerate(conditions):
            cond_id = f"ev:cond:{rule_triggered}:{idx}"
            cond_copy = dict(cond)
            cond_copy["evidence_pointer"] = cond_id
            cond_pointers.append(cond_id)
            nodes.append({"id": cond_id, "type": "RULE_CONDITION", "evidence_pointer": cond_id, "data": cond_copy})
            edges.append({"source": alert_node_id, "target": cond_id, "relation": "TRIGGERED_CONDITION"})

        customer_node_id = None
        if customer_id:
            customer_node_id = f"ev:cust:{customer_id}"
            nodes.append(
                {
                    "id": customer_node_id,
                    "type": "CUSTOMER",
                    "evidence_pointer": customer_node_id,
                    "data": {"customer_id": customer_id, "snapshot": customer_snapshot or {}},
                }
            )
            edges.append({"source": alert_node_id, "target": customer_node_id, "relation": "HAS_CUSTOMER"})

        transaction_node_id = None
        if transaction_id:
            transaction_node_id = f"ev:tx:{transaction_id}"
            nodes.append(
                {
                    "id": transaction_node_id,
                    "type": "TRANSACTION",
                    "evidence_pointer": transaction_node_id,
                    "data": {"transaction_id": transaction_id, "snapshot": transaction_snapshot or {}},
                }
            )
            edges.append({"source": alert_node_id, "target": transaction_node_id, "relation": "HAS_TRANSACTION"})

        aggregate_node_id = None
        if aggregate_payload:
            aggregate_node_id = f"ev:agg:{customer_id or 'na'}:{rule_triggered}:{window_days if window_days is not None else 'na'}"
            nodes.append(
                {
                    "id": aggregate_node_id,
                    "type": "AGGREGATE",
                    "evidence_pointer": aggregate_node_id,
                    "data": aggregate_payload,
                }
            )
            if customer_node_id:
                edges.append({"source": customer_node_id, "target": aggregate_node_id, "relation": "HAS_AGGREGATES"})
            for cond_ptr in cond_pointers:
                edges.append({"source": cond_ptr, "target": aggregate_node_id, "relation": "EVIDENCED_BY"})

        for hit in sanctions_hits:
            hit_id = hit.get("hit_id", "NOT_PROVIDED")
            hit_node_id = f"ev:sanction:{hit_id}"
            nodes.append(
                {
                    "id": hit_node_id,
                    "type": "SANCTIONS_HIT",
                    "evidence_pointer": hit_node_id,
                    "data": hit,
                }
            )
            edges.append({"source": alert_node_id, "target": hit_node_id, "relation": "HAS_SANCTIONS_HIT"})

        evidence_pointers = cond_pointers or [alert_node_id]
        citations = match_citations(
            db=db,
            bank_id=bank_id,
            alert_type=alert.get("alert_type", "AML"),
            rule_triggered=rule_triggered,
            evidence_pointers=evidence_pointers,
            rule_description=alert.get("rule_description"),
            conditions_triggered=conditions,
        )
        for citation in citations:
            cid = citation["citation_id"]
            law_node_id = f"ev:law:{cid}"
            nodes.append(
                {
                    "id": law_node_id,
                    "type": "LAW_CITATION",
                    "evidence_pointer": law_node_id,
                    "data": citation,
                }
            )
            edges.append({"source": alert_node_id, "target": law_node_id, "relation": "CITED_BY"})

        source_payload = {
            "alert": alert,
            "customer": customer_snapshot or "NOT PROVIDED",
            "transaction": transaction_snapshot or "NOT PROVIDED",
            "aggregates": aggregate_payload or "NOT PROVIDED",
            "sanctions_hits": sanctions_hits or "NOT PROVIDED",
        }

        graph: dict[str, Any] = {
            "schema_version": "1.0",
            "bank_id": bank_id,
            "alert_id": alert_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_payload_hash": sha256_json(source_payload),
            "nodes": nodes,
            "edges": edges,
            "missing_evidence": missing,
        }
        graph["evidence_hash"] = sha256_json(graph)

        validate_json("evidence_graph.schema.json", graph)
        return graph
