from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.db.session import get_db
from core.services.connector_client import ConnectorClient
from core.services.orchestrator import OrchestratorService
from core.utils.request_context import request_id_ctx

router = APIRouter(prefix="/v1/demo", tags=["demo"])


class DemoGenerateCaseRequest(BaseModel):
    bank_id: str = Field(default="demo", min_length=1)
    kind: Literal["AML", "SANCTIONS"]


class DemoGenerateCaseResponse(BaseModel):
    bank_id: str
    alert_id: str
    workflow_run_id: str
    case_id: str
    status: str


@router.post("/generate-case", response_model=DemoGenerateCaseResponse)
def generate_demo_case(payload: DemoGenerateCaseRequest, db: Session = Depends(get_db)) -> DemoGenerateCaseResponse:
    """
    Create exactly one synthetic alert inside the connector for `bank_id`, then synchronously generate a casefile.
    """
    connector = ConnectorClient()
    orchestrator = OrchestratorService()

    try:
        emit_result = connector.emit_demo_alert(kind=payload.kind, bank_id=payload.bank_id)
        alert_id = str(emit_result.get("alert_id") or "")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Connector emit failed: {exc}") from exc

    if not alert_id:
        raise HTTPException(status_code=500, detail="Connector did not return alert_id")

    workflow = orchestrator.create_workflow_run(
        db=db,
        alert_id=alert_id,
        bank_id=payload.bank_id,
        request_id=request_id_ctx.get(),
    )

    case_row = orchestrator.pull_and_generate_case(
        db=db,
        alert_id=alert_id,
        bank_id=payload.bank_id,
        workflow_run_id=workflow.workflow_run_id,
        actor_id="api-demo",
    )

    return DemoGenerateCaseResponse(
        bank_id=payload.bank_id,
        alert_id=alert_id,
        workflow_run_id=workflow.workflow_run_id,
        case_id=case_row.case_id,
        status=case_row.status,
    )

