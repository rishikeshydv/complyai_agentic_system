from __future__ import annotations

from core.db.models import Case


def serialize_case(row: Case) -> dict:
    return {
        "case_id": row.case_id,
        "alert_id": row.alert_id,
        "bank_id": row.bank_id,
        "alert_type": row.alert_type,
        "status": row.status,
        "casefile_json": row.casefile_json,
        "casefile_markdown": row.casefile_markdown,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "integrity": {
            "source_payload_sha256": row.casefile_json.get("export_bundle", {}).get("source_payload_hash", "NOT PROVIDED"),
            "evidence_sha256": row.evidence_hash,
            "export_id": row.casefile_json.get("export_bundle", {}).get("export_id", "NOT PROVIDED"),
        },
    }
