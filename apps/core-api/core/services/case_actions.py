from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from core.db.models import Case
from core.services.governance_service import append_audit_event
from core.utils.hashing import sha256_json
from core.utils.template_loader import render_markdown

ACTION_TO_STATUS = {
    "REVIEW": "REVIEWED",
    "ESCALATE": "ESCALATED",
    "CLOSE": "CLOSED",
    "REQUEST_SAR_DRAFT": "SAR_DRAFTED",
    "APPROVE_SAR": "SAR_APPROVED",
    "MARK_SAR_FILED": "SAR_FILED",
}


def apply_case_action(
    db: Session,
    case_row: Case,
    action: str,
    actor_id: str,
    notes: str | None,
    sar_narrative: str | None,
) -> Case:
    if action not in ACTION_TO_STATUS:
        raise ValueError("Unsupported action")

    new_status = ACTION_TO_STATUS[action]
    case_row.status = new_status
    casefile = dict(case_row.casefile_json)
    casefile["header"]["status"] = new_status

    if action == "REQUEST_SAR_DRAFT":
        sar = dict(casefile.get("sar_draft", {}))
        sar["required"] = True
        if sar_narrative:
            sar["narrative_draft"] = sar_narrative
        else:
            sar.setdefault("narrative_draft", "NOT PROVIDED")
        sar.setdefault("fields", {})
        sar.setdefault("evidence_pointers", ["NOT PROVIDED"])
        casefile["sar_draft"] = sar

    events = casefile.get("timeline_and_audit", {}).get("events", [])
    event = {
        "action": action,
        "actor_type": "HUMAN",
        "actor_id": actor_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "notes": notes or f"Case action {action}",
        "metadata": {"new_status": new_status},
    }
    events.append(event)
    casefile["timeline_and_audit"] = {"events": events}

    casefile_hash = sha256_json({**casefile, "export_bundle": {**casefile["export_bundle"], "casefile_hash": "PENDING"}})
    casefile["export_bundle"]["casefile_hash"] = casefile_hash

    case_row.casefile_json = casefile
    case_row.casefile_hash = casefile_hash
    case_row.casefile_markdown = render_markdown("casefile.md.j2", {"casefile": casefile})

    db.add(case_row)
    db.commit()
    db.refresh(case_row)

    append_audit_event(
        db,
        case_id=case_row.case_id,
        workflow_run_id=None,
        actor_type="HUMAN",
        actor_id=actor_id,
        action=action,
        notes=notes or f"Case action {action}",
        metadata={"status": new_status},
    )

    return case_row
