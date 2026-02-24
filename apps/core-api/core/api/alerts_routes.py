from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.celery_app import celery_app
from core.config import settings
from core.db.session import get_db
from core.schemas.cases import AlertEventRequest, IngestionPollResponse, PullAlertResponse
from core.services.auto_ingest_service import AutoIngestService
from core.services.orchestrator import OrchestratorService
from core.utils.request_context import request_id_ctx

router = APIRouter(prefix="/v1/alerts", tags=["alerts"])


@router.post("/{alert_id}/pull", response_model=PullAlertResponse)
def pull_alert(
    alert_id: str,
    bank_id: str = Query(default="demo"),
    sync: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> PullAlertResponse:
    orchestrator = OrchestratorService()
    workflow = orchestrator.create_workflow_run(db, alert_id=alert_id, bank_id=bank_id, request_id=request_id_ctx.get())

    if sync or settings.celery_task_always_eager:
        case_row = orchestrator.pull_and_generate_case(
            db=db,
            alert_id=alert_id,
            bank_id=bank_id,
            workflow_run_id=workflow.workflow_run_id,
            actor_id="api-manual",
        )
        return PullAlertResponse(
            workflow_run_id=workflow.workflow_run_id,
            status=case_row.status,
            case_id=case_row.case_id,
        )

    celery_app.send_task(
        "pull_and_generate_case",
        kwargs={"alert_id": alert_id, "bank_id": bank_id, "workflow_run_id": workflow.workflow_run_id},
    )
    return PullAlertResponse(workflow_run_id=workflow.workflow_run_id, status="QUEUED")


@router.post("/ingestion/poll", response_model=IngestionPollResponse)
def poll_ingestion(
    db: Session = Depends(get_db),
) -> IngestionPollResponse:
    service = AutoIngestService()
    result = service.poll_and_dispatch(db=db, actor_id="api-poll")
    return IngestionPollResponse(**result)


@router.post("/events")
def ingest_alert_event(
    payload: AlertEventRequest,
    db: Session = Depends(get_db),
):
    service = AutoIngestService()
    queued, error = service.dispatch_alert_event(
        db=db,
        bank_id=payload.bank_id,
        alert_id=payload.alert_id,
        source_event_id=payload.source_event_id,
        event_created_at=payload.created_at,
        actor_id="api-event-ingest",
    )
    return {
        "accepted": queued,
        "deduped": not queued and error is None,
        "error": error,
    }
