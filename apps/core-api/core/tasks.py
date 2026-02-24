from __future__ import annotations

from celery import shared_task

from core.config import settings
from core.db.models import Case
from core.db.session import SessionLocal
from core.services.auto_ingest_service import AutoIngestService, mark_ingest_event_by_workflow
from core.services.case_actions import apply_case_action
from core.services.orchestrator import OrchestratorService


@shared_task(name="pull_and_generate_case")
def pull_and_generate_case(alert_id: str, bank_id: str, workflow_run_id: str) -> dict:
    db = SessionLocal()
    try:
        orchestrator = OrchestratorService()
        try:
            case_row = orchestrator.pull_and_generate_case(
                db=db,
                alert_id=alert_id,
                bank_id=bank_id,
                workflow_run_id=workflow_run_id,
                actor_id="core-worker",
            )
            mark_ingest_event_by_workflow(
                db=db,
                workflow_run_id=workflow_run_id,
                status="COMPLETED",
                case_id=case_row.case_id,
            )
        except Exception as exc:
            mark_ingest_event_by_workflow(
                db=db,
                workflow_run_id=workflow_run_id,
                status="FAILED",
                error_message=str(exc),
            )
            raise
        return {"workflow_run_id": workflow_run_id, "case_id": case_row.case_id, "status": case_row.status}
    finally:
        db.close()


@shared_task(name="generate_sar")
def generate_sar(case_id: str) -> dict:
    db = SessionLocal()
    try:
        row = db.get(Case, case_id)
        if not row:
            raise ValueError("Case not found")
        updated = apply_case_action(
            db=db,
            case_row=row,
            action="REQUEST_SAR_DRAFT",
            actor_id="core-worker",
            notes="Generated SAR draft via worker task",
            sar_narrative=row.casefile_json.get("sar_draft", {}).get("narrative_draft", "NOT PROVIDED"),
        )
        return {"case_id": updated.case_id, "status": updated.status}
    finally:
        db.close()


@shared_task(name="repair_casefile")
def repair_casefile(case_id: str) -> dict:
    db = SessionLocal()
    try:
        row = db.get(Case, case_id)
        if not row:
            raise ValueError("Case not found")
        orchestrator = OrchestratorService()
        result = orchestrator.replay_casefile(db=db, case_row=row, apply_changes=True)
        return result
    finally:
        db.close()


@shared_task(name="poll_connector_alerts")
def poll_connector_alerts() -> dict:
    if not settings.auto_ingest_enabled:
        return {"enabled": False, "queued": 0, "deduped": 0, "errors": 0, "discovered": 0, "banks": []}

    db = SessionLocal()
    try:
        service = AutoIngestService()
        return service.poll_and_dispatch(db=db, actor_id="auto-ingest-worker")
    finally:
        db.close()
