from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from core.db.models import AlertIngestEvent, AuditEvent, Case, ConnectorPollState, EvidenceSnapshot, LLMInvocation, WorkflowRun
from core.services.auto_ingest_service import AutoIngestService
from core.services.connector_client import ConnectorClient
from core.services.governance_service import append_audit_event


class PlaygroundService:
    def __init__(self, connector_client: ConnectorClient | None = None) -> None:
        self.connector = connector_client or ConnectorClient()
        self.auto_ingest = AutoIngestService(connector_client=self.connector)

    def _pipeline_metrics(self, db: Session, bank_id: str) -> dict[str, Any]:
        since = datetime.utcnow() - timedelta(hours=1)
        case_rows = db.scalars(select(Case).where(Case.bank_id == bank_id).order_by(Case.created_at.desc())).all()
        ingest_rows = db.scalars(
            select(AlertIngestEvent).where(AlertIngestEvent.bank_id == bank_id).order_by(AlertIngestEvent.id.desc())
        ).all()

        recent_ingests = [row for row in ingest_rows if row.created_at >= since]
        recent_cases = [row for row in case_rows if row.created_at >= since]

        return {
            "total_cases": len(case_rows),
            "ready_for_review": len([row for row in case_rows if row.status == "READY_FOR_REVIEW"]),
            "sar_flow_cases": len([row for row in case_rows if "SAR" in row.status]),
            "ingestion_events_total": len(ingest_rows),
            "ingestion_events_last_hour": len(recent_ingests),
            "cases_last_hour": len(recent_cases),
            "latest_case_id": case_rows[0].case_id if case_rows else None,
            "latest_ingest_status": ingest_rows[0].status if ingest_rows else None,
        }

    def _reset_pipeline_data(self, db: Session, bank_id: str) -> None:
        case_ids = db.scalars(select(Case.case_id).where(Case.bank_id == bank_id)).all()
        workflow_run_ids = db.scalars(select(WorkflowRun.workflow_run_id).where(WorkflowRun.bank_id == bank_id)).all()

        if case_ids:
            db.execute(delete(LLMInvocation).where(LLMInvocation.case_id.in_(case_ids)))
            db.execute(delete(AuditEvent).where(AuditEvent.case_id.in_(case_ids)))
        if workflow_run_ids:
            db.execute(delete(LLMInvocation).where(LLMInvocation.workflow_run_id.in_(workflow_run_ids)))
            db.execute(delete(AuditEvent).where(AuditEvent.workflow_run_id.in_(workflow_run_ids)))

        db.execute(delete(Case).where(Case.bank_id == bank_id))
        db.execute(delete(EvidenceSnapshot).where(EvidenceSnapshot.bank_id == bank_id))
        db.execute(delete(WorkflowRun).where(WorkflowRun.bank_id == bank_id))
        db.execute(delete(AlertIngestEvent).where(AlertIngestEvent.bank_id == bank_id))
        db.execute(delete(ConnectorPollState).where(ConnectorPollState.bank_id == bank_id))
        db.commit()

    def status(self, db: Session, bank_id: str = "demo") -> dict[str, Any]:
        simulator = self.connector.simulator_status(bank_id=bank_id)
        return {
            "bank_id": bank_id,
            "simulator": simulator,
            "pipeline": self._pipeline_metrics(db=db, bank_id=bank_id),
        }

    def start(
        self,
        db: Session,
        bank_id: str,
        seed_customers: int,
        tx_per_tick: int,
        aml_alert_rate: float,
        sanctions_alert_rate: float,
        actor_id: str,
        reset_before_start: bool = True,
    ) -> dict[str, Any]:
        if reset_before_start:
            self._reset_pipeline_data(db=db, bank_id=bank_id)
            append_audit_event(
                db=db,
                case_id=None,
                workflow_run_id=None,
                actor_type="SYSTEM",
                actor_id=actor_id,
                action="PLAYGROUND_PIPELINE_RESET",
                notes="Reset playground simulator + pipeline state before start",
                metadata={"bank_id": bank_id},
            )

        simulator = self.connector.simulator_start(
            bank_id=bank_id,
            seed_customers=seed_customers,
            tx_per_tick=tx_per_tick,
            aml_alert_rate=aml_alert_rate,
            sanctions_alert_rate=sanctions_alert_rate,
            reset_before_start=reset_before_start,
        )
        append_audit_event(
            db=db,
            case_id=None,
            workflow_run_id=None,
            actor_type="SYSTEM",
            actor_id=actor_id,
            action="PLAYGROUND_SIM_STARTED",
            notes="Started transaction simulator",
            metadata={
                "bank_id": bank_id,
                "config": simulator.get("config", {}),
                "reset_before_start": reset_before_start,
            },
        )
        return {
            "bank_id": bank_id,
            "simulator": simulator,
            "pipeline": self._pipeline_metrics(db=db, bank_id=bank_id),
        }

    def stop(self, db: Session, bank_id: str, actor_id: str) -> dict[str, Any]:
        simulator = self.connector.simulator_stop(bank_id=bank_id)
        append_audit_event(
            db=db,
            case_id=None,
            workflow_run_id=None,
            actor_type="SYSTEM",
            actor_id=actor_id,
            action="PLAYGROUND_SIM_STOPPED",
            notes="Stopped transaction simulator",
            metadata={"bank_id": bank_id},
        )
        return {
            "bank_id": bank_id,
            "simulator": simulator,
            "pipeline": self._pipeline_metrics(db=db, bank_id=bank_id),
        }

    def tick(
        self,
        db: Session,
        bank_id: str,
        count: int,
        run_ingestion_poll: bool,
        actor_id: str,
    ) -> dict[str, Any]:
        simulator = self.connector.simulator_tick(count=count, bank_id=bank_id)
        poll_result: dict[str, Any] | None = None
        if run_ingestion_poll:
            poll_result = self.auto_ingest.poll_and_dispatch(db=db, actor_id=actor_id)

        append_audit_event(
            db=db,
            case_id=None,
            workflow_run_id=None,
            actor_type="SYSTEM",
            actor_id=actor_id,
            action="PLAYGROUND_SIM_TICK",
            notes=f"Executed simulator tick x{count}",
            metadata={"bank_id": bank_id, "count": count, "run_ingestion_poll": run_ingestion_poll},
        )
        payload = {
            "bank_id": bank_id,
            "simulator": simulator,
            "pipeline": self._pipeline_metrics(db=db, bank_id=bank_id),
        }
        if poll_result is not None:
            payload["ingestion_poll"] = poll_result
        return payload
