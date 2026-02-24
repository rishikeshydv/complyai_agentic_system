from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.db.models import AuditEvent, Case, EvidenceSnapshot, LLMInvocation, WorkflowRun
from core.db.session import get_db
from core.schemas.cases import CaseActionRequest, CaseRecord, ReplayResponse
from core.services.case_actions import apply_case_action
from core.services.orchestrator import OrchestratorService
from core.utils.schema_loader import validate_json
from core.api.helpers import serialize_case

router = APIRouter(prefix="/v1/cases", tags=["cases"])


@router.get("", response_model=list[CaseRecord])
def list_cases(
    bank_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    alert_type: str | None = Query(default=None),
    created_after: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = select(Case).order_by(Case.created_at.desc())
    if bank_id:
        query = query.where(Case.bank_id == bank_id)
    if status:
        query = query.where(Case.status == status)
    if alert_type:
        query = query.where(Case.alert_type == alert_type)
    if created_after:
        try:
            dt = datetime.fromisoformat(created_after)
            query = query.where(Case.created_at >= dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="created_after must be ISO datetime")

    rows = db.scalars(query).all()
    return [serialize_case(row) for row in rows]


@router.get("/{case_id}", response_model=CaseRecord)
def get_case(
    case_id: str,
    db: Session = Depends(get_db),
):
    row = db.get(Case, case_id)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    return serialize_case(row)


@router.get("/{case_id}/export/markdown")
def export_markdown(
    case_id: str,
    db: Session = Depends(get_db),
):
    row = db.get(Case, case_id)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    return Response(content=row.casefile_markdown, media_type="text/markdown; charset=utf-8")


@router.get("/{case_id}/export/json")
def export_json(
    case_id: str,
    db: Session = Depends(get_db),
):
    row = db.get(Case, case_id)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    return row.casefile_json


@router.get("/{case_id}/export/exam-packet")
def export_exam_packet(
    case_id: str,
    db: Session = Depends(get_db),
):
    """
    Downloads a single ZIP "exam packet" suitable for audits/diligence:
    - cover.md (explains evidence pointers, hashes, and replayability)
    - casefile.md
    - casefile.json
    - evidence_snapshot.json
    - manifest.json (file hashes + versions)
    """
    row = db.get(Case, case_id)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")

    snapshot = db.get(EvidenceSnapshot, row.evidence_snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=500, detail="Evidence snapshot missing")

    export_bundle = row.casefile_json.get("export_bundle", {}) if isinstance(row.casefile_json, dict) else {}

    cover = (
        "# Comply AI Exam Packet\n\n"
        "This bundle contains a single, discrete case file and its backing evidence snapshot.\n\n"
        "## How to Read\n"
        "- **Evidence pointers** look like `ev:...` and refer to nodes in `evidence_snapshot.json`.\n"
        "- If a fact is not present in the evidence snapshot, the platform should output `NOT PROVIDED`.\n\n"
        "## Integrity\n"
        f"- Case ID: `{row.case_id}`\n"
        f"- Alert ID: `{row.alert_id}`\n"
        f"- Bank ID: `{row.bank_id}`\n"
        f"- Evidence hash: `{row.evidence_hash}`\n"
        f"- Casefile hash: `{row.casefile_hash}`\n\n"
        "## Replayability\n"
        "The casefile can be regenerated deterministically from the evidence snapshot and compared (diff) to confirm reproducibility.\n\n"
        "## Files\n"
        "- `casefile.md`: analyst-readable report\n"
        "- `casefile.json`: structured casefile output\n"
        "- `evidence_snapshot.json`: immutable evidence graph used for generation\n"
        "- `manifest.json`: file hashes and version metadata\n"
    )

    files: dict[str, bytes] = {
        "cover.md": cover.encode("utf-8"),
        "casefile.md": (row.casefile_markdown or "").encode("utf-8"),
        "casefile.json": json.dumps(row.casefile_json, indent=2, sort_keys=True).encode("utf-8"),
        "evidence_snapshot.json": json.dumps(snapshot.graph_json, indent=2, sort_keys=True).encode("utf-8"),
    }

    def sha256_bytes(payload: bytes) -> str:
        return hashlib.sha256(payload).hexdigest()

    manifest = {
        "case_id": row.case_id,
        "alert_id": row.alert_id,
        "bank_id": row.bank_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "evidence_hash": row.evidence_hash,
        "casefile_hash": row.casefile_hash,
        "export_bundle": export_bundle,
        "files": [
            {"path": name, "sha256": sha256_bytes(content), "bytes": len(content)}
            for name, content in sorted(files.items(), key=lambda x: x[0])
        ],
    }
    files["manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    buf.seek(0)

    filename = f"complyai_exam_packet_{row.case_id}.zip"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(buf, media_type="application/zip", headers=headers)


@router.get("/{case_id}/audit-events")
def get_case_audit_events(
    case_id: str,
    db: Session = Depends(get_db),
):
    row = db.get(Case, case_id)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    events = db.scalars(
        select(AuditEvent).where(AuditEvent.case_id == case_id).order_by(AuditEvent.created_at.asc())
    ).all()
    return [
        {
            "event_id": ev.event_id,
            "workflow_run_id": ev.workflow_run_id,
            "actor_type": ev.actor_type,
            "actor_id": ev.actor_id,
            "action": ev.action,
            "notes": ev.notes,
            "metadata": ev.metadata_jsonb,
            "created_at": ev.created_at,
        }
        for ev in events
    ]


@router.get("/{case_id}/llm-invocations")
def get_case_llm_invocations(
    case_id: str,
    db: Session = Depends(get_db),
):
    row = db.get(Case, case_id)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")

    workflow_ids = list(
        db.scalars(
            select(WorkflowRun.workflow_run_id).where(
                WorkflowRun.case_id == case_id
            )
        ).all()
    )

    if workflow_ids:
        invocations = db.scalars(
            select(LLMInvocation)
            .where((LLMInvocation.case_id == case_id) | (LLMInvocation.workflow_run_id.in_(workflow_ids)))
            .order_by(LLMInvocation.created_at.asc())
        ).all()
    else:
        invocations = db.scalars(
            select(LLMInvocation).where(LLMInvocation.case_id == case_id).order_by(LLMInvocation.created_at.asc())
        ).all()
    return [
        {
            "id": item.id,
            "workflow_run_id": item.workflow_run_id,
            "prompt_id": item.prompt_id,
            "version": item.version,
            "rendered_prompt_hash": item.rendered_prompt_hash,
            "model_provider": item.model_provider,
            "model_name": item.model_name,
            "response_hash": item.response_hash,
            "created_at": item.created_at,
        }
        for item in invocations
    ]


@router.post("/{case_id}/actions", response_model=CaseRecord)
def case_action(
    case_id: str,
    payload: CaseActionRequest,
    db: Session = Depends(get_db),
):
    validate_json(
        "action_request.schema.json",
        {
            "action": payload.action,
            "actor_id": payload.actor_id,
            "notes": payload.notes,
            "sar_narrative": payload.sar_narrative,
        },
    )

    row = db.get(Case, case_id)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")

    updated = apply_case_action(
        db=db,
        case_row=row,
        action=payload.action,
        actor_id=payload.actor_id,
        notes=payload.notes,
        sar_narrative=payload.sar_narrative,
    )
    return serialize_case(updated)


@router.post("/{case_id}/replay", response_model=ReplayResponse)
def replay_case(
    case_id: str,
    apply_changes: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    row = db.get(Case, case_id)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    orchestrator = OrchestratorService()
    result = orchestrator.replay_casefile(db=db, case_row=row, apply_changes=apply_changes)
    return ReplayResponse(**result)
