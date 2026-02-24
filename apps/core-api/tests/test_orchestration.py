from __future__ import annotations

import os

from sqlalchemy import select

os.environ["CORE_DB_URL"] = "sqlite:///file:core_test?mode=memory&cache=shared&uri=true"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["AUTO_INGEST_ENABLED"] = "true"

from core.db.models import AlertIngestEvent, AuditEvent, Base, Case
from core.db.seed import seed
from core.db.session import SessionLocal, engine
from core.services.auto_ingest_service import AutoIngestService
from core.services.evidence_service import EvidenceService
from core.services.law_matcher import match_citations
from core.services.orchestrator import OrchestratorService
from core.services.playground_service import PlaygroundService


class FakeConnectorClient:
    simulator_running = False
    simulator_tx_generated = 0
    simulator_alerts_generated = 0

    @staticmethod
    def _feed_item(alert_id: str, alert_type: str, rule_triggered: str, customer_id: str, transaction_id: str | None, created_at: str):
        return {
            "alert_id": alert_id,
            "alert_type": alert_type,
            "rule_triggered": rule_triggered,
            "customer_id": customer_id,
            "transaction_id": transaction_id,
            "created_at": created_at,
            "source_event_id": f"{alert_id}:{created_at}",
        }

    def fetch_alert_feed(self, created_after: str | None = None, limit: int = 100, bank_id: str | None = None):
        items = [
            self._feed_item("ALERT-001", "AML", "CASH_SPIKE_30D", "CUST-10009", "TX-928771", "2026-02-08T01:00:00Z"),
        ]
        if created_after:
            items = [item for item in items if item["created_at"] > created_after]
        return {"items": items[:limit], "count": min(len(items), limit)}

    def fetch_alert(self, alert_id: str):
        if alert_id == "ALERT-002":
            return {
                "alert_id": alert_id,
                "alert_type": "SANCTIONS",
                "alert_metadata": {"source_system": "sanctions-screening"},
                "rule_triggered": "OFAC_NAME_SCREEN_MATCH",
                "rule_description": "Name matched sanctions list",
                "rule_thresholds": {"score_threshold": 0.85},
                "rule_evaluation": {
                    "conditions_triggered": [
                        {
                            "field": "screening.score",
                            "operator": ">=",
                            "threshold": 0.85,
                            "actual": 0.92,
                            "window_days": None,
                        }
                    ]
                },
                "transaction_id": None,
                "customer_id": "CUST-20021",
                "sanctions_hit_preview": {"hit_id": "HIT-OFAC-7781", "score": 0.92},
            }

        return {
            "alert_id": alert_id,
            "alert_type": "AML",
            "alert_metadata": {"source_system": "core-aml-rules-engine"},
            "rule_triggered": "CASH_SPIKE_30D",
            "rule_description": "30-day cash deposits exceeded profile threshold",
            "rule_thresholds": {"cash_deposit_total_30d": 25000, "cash_deposit_count_30d": 8},
            "rule_evaluation": {
                "conditions_triggered": [
                    {
                        "field": "historical_aggregates.cash_deposit_total_30d",
                        "operator": ">=",
                        "threshold": 25000,
                        "actual": 31250,
                        "window_days": 30,
                    }
                ]
            },
            "transaction_id": "TX-928771",
            "customer_id": "CUST-10009",
            "sanctions_hit_preview": None,
        }

    def fetch_transaction(self, transaction_id: str):
        return {
            "transaction_id": transaction_id,
            "snapshot": {
                "transaction_id": transaction_id,
                "type": "cash_deposit",
                "amount": 9500,
                "currency": "USD",
                "channel": "branch",
                "occurred_at": "2026-02-06T19:00:00Z",
                "description": "Business cash intake",
            },
        }

    def fetch_customer(self, customer_id: str):
        return {
            "customer_id": customer_id,
            "snapshot": {
                "customer_id": customer_id,
                "customer_type": "SMB",
                "segment": "Hospitality",
                "kyc_risk_rating": "High",
                "edd": True,
                "prior_alerts_12m": 2,
                "prior_sar_12m": 0,
            },
        }

    def fetch_aggregates(self, customer_id: str, rule_triggered: str, window_days: int | None):
        return {
            "customer_id": customer_id,
            "rule_triggered": rule_triggered,
            "window_days": window_days,
            "aggregates": {
                "avg_cash_deposit_90d": 2800,
                "cash_deposit_count_30d": 11,
                "cash_deposit_total_30d": 31250,
            },
            "linked_transactions": [
                {"transaction_id": "TX-928700", "description": "cash deposit 7,900"}
            ],
        }

    def fetch_sanctions_hits(self, alert_id: str):
        return {
            "alert_id": alert_id,
            "hits": [
                {
                    "hit_id": "HIT-OFAC-7781",
                    "list_source": "OFAC SDN",
                    "matched_fields": ["full_name"],
                    "score": 0.92,
                    "features": {"name_similarity": 0.96},
                    "prior_decision": "NOT PROVIDED",
                }
            ],
        }

    def simulator_status(self, bank_id: str | None = None):
        return {
            "running": self.simulator_running,
            "config": {
                "bank_id": bank_id or "demo",
                "seed_customers": 20,
                "tx_per_tick": 12,
                "aml_alert_rate": 0.2,
                "sanctions_alert_rate": 0.05,
            },
            "started_at": "2026-02-09T00:00:00Z",
            "last_tick_at": "2026-02-09T00:01:00Z",
            "totals": {
                "transactions_generated": self.simulator_tx_generated,
                "alerts_generated": self.simulator_alerts_generated,
                "aml_alerts_generated": self.simulator_alerts_generated,
                "sanctions_alerts_generated": 0,
                "customers_in_store": 20,
                "transactions_in_store": 100,
                "alerts_in_store": 2,
                "latest_alert_id": "ALERT-001",
            },
        }

    def simulator_start(
        self,
        bank_id: str = "demo",
        seed_customers: int = 20,
        tx_per_tick: int = 12,
        aml_alert_rate: float = 0.2,
        sanctions_alert_rate: float = 0.05,
        reset_before_start: bool = True,
    ):
        if reset_before_start:
            self.simulator_tx_generated = 0
            self.simulator_alerts_generated = 0
        self.simulator_running = True
        return self.simulator_status(bank_id=bank_id)

    def simulator_stop(self, bank_id: str = "demo"):
        self.simulator_running = False
        return self.simulator_status(bank_id=bank_id)

    def simulator_tick(self, count: int = 1, bank_id: str = "demo"):
        self.simulator_tx_generated += count * 12
        self.simulator_alerts_generated += count
        return self.simulator_status(bank_id=bank_id)


def setup_module() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed()


def test_evidence_graph_contains_required_nodes_and_edges() -> None:
    db = SessionLocal()
    try:
        service = EvidenceService(connector_client=FakeConnectorClient())
        graph = service.build_evidence_graph(db=db, alert_id="ALERT-001", bank_id="demo")
        node_types = {n["type"] for n in graph["nodes"]}
        assert "ALERT" in node_types
        assert "RULE_CONDITION" in node_types
        assert "CUSTOMER" in node_types
        assert "AGGREGATE" in node_types
        assert "LAW_CITATION" in node_types
        assert graph["edges"]
        assert graph["evidence_hash"]
        assert graph["source_payload_hash"]
    finally:
        db.close()


def test_orchestrator_produces_ready_casefile_with_mock_llm() -> None:
    db = SessionLocal()
    try:
        orchestrator = OrchestratorService()
        orchestrator.evidence_service = EvidenceService(connector_client=FakeConnectorClient())

        wf = orchestrator.create_workflow_run(db, alert_id="ALERT-001", bank_id="demo", request_id="test")
        case_row = orchestrator.pull_and_generate_case(
            db=db,
            alert_id="ALERT-001",
            bank_id="demo",
            workflow_run_id=wf.workflow_run_id,
            actor_id="pytest",
        )

        assert case_row.status == "READY_FOR_REVIEW"
        assert case_row.casefile_json["evidence_hash"]
        assert case_row.casefile_json["export_bundle"]["source_payload_hash"]
        assert case_row.casefile_json["executive_summary"]["bullets"]
    finally:
        db.close()


def test_governance_audit_log_contains_key_events() -> None:
    db = SessionLocal()
    try:
        orchestrator = OrchestratorService()
        orchestrator.evidence_service = EvidenceService(connector_client=FakeConnectorClient())

        wf = orchestrator.create_workflow_run(db, alert_id="ALERT-002", bank_id="demo", request_id="test2")
        orchestrator.pull_and_generate_case(
            db=db,
            alert_id="ALERT-002",
            bank_id="demo",
            workflow_run_id=wf.workflow_run_id,
            actor_id="pytest",
        )

        actions = [
            row.action
            for row in db.scalars(select(AuditEvent).where(AuditEvent.workflow_run_id == wf.workflow_run_id)).all()
        ]
        assert "WORKFLOW_STARTED" in actions
        assert "CASEFILE_GENERATED" in actions
    finally:
        db.close()


def test_auto_ingest_polls_and_dedupes_alerts() -> None:
    db = SessionLocal()
    try:
        starting_cases = len(db.scalars(select(Case)).all())

        def orchestrator_factory() -> OrchestratorService:
            orchestrator = OrchestratorService()
            orchestrator.evidence_service = EvidenceService(connector_client=FakeConnectorClient())
            return orchestrator

        service = AutoIngestService(
            connector_client=FakeConnectorClient(),
            orchestrator_factory=orchestrator_factory,
        )

        first = service.poll_and_dispatch(db=db, actor_id="pytest-auto")
        second = service.poll_and_dispatch(db=db, actor_id="pytest-auto")

        total_cases = len(db.scalars(select(Case)).all())
        queued_events = db.scalars(select(AlertIngestEvent)).all()

        assert first["queued"] == 1
        assert first["errors"] == 0
        assert second["queued"] == 0
        assert second["deduped"] >= 1
        assert total_cases == starting_cases + 1
        assert queued_events[0].status == "COMPLETED"
    finally:
        db.close()


def test_playground_service_start_tick_stop() -> None:
    db = SessionLocal()
    try:
        connector = FakeConnectorClient()
        service = PlaygroundService(connector_client=connector)

        started = service.start(
            db=db,
            bank_id="demo",
            seed_customers=20,
            tx_per_tick=10,
            aml_alert_rate=0.2,
            sanctions_alert_rate=0.05,
            actor_id="pytest",
        )
        assert started["simulator"]["running"] is True
        assert started["pipeline"]["total_cases"] == 0
        assert started["pipeline"]["ingestion_events_total"] == 0

        ticked = service.tick(
            db=db,
            bank_id="demo",
            count=2,
            run_ingestion_poll=True,
            actor_id="pytest",
        )
        assert ticked["simulator"]["totals"]["transactions_generated"] >= 24
        assert "ingestion_poll" in ticked

        stopped = service.stop(db=db, bank_id="demo", actor_id="pytest")
        assert stopped["simulator"]["running"] is False
    finally:
        db.close()


def test_law_mapping_v2_deterministic_path() -> None:
    db = SessionLocal()
    try:
        citations = match_citations(
            db=db,
            bank_id="demo",
            alert_type="AML",
            rule_triggered="STRUCTURING_RULE_03",
            evidence_pointers=["ev:cond:STRUCTURING_RULE_03:0"],
            rule_description="Repeated cash deposits near threshold",
            conditions_triggered=[
                {
                    "field": "historical_aggregates.cash_deposit_count_7d",
                    "operator": ">=",
                    "threshold": 3,
                    "actual": 4,
                }
            ],
        )
        assert citations
        assert citations[0]["mapping_mode"] == "deterministic"
        assert citations[0]["evidence_pointers"][0].startswith("ev:")
    finally:
        db.close()
