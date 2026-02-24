from __future__ import annotations

import json

from sqlalchemy import create_engine, text

from core.config import settings


# This is intentionally limited to generated runtime data for the demo/playground.
# It should not delete regulatory documents, mappings, laws KB, or users.
TABLES_TO_TRUNCATE: list[str] = [
    # Core runtime tables
    "llm_invocations",
    "audit_events",
    "alert_ingest_events",
    "connector_poll_state",
    "cases",
    "evidence_snapshots",
    "workflow_runs",
    # Connector demo tables (in this Railway deployment both services share the same Postgres)
    "connector_fetch_audit",
    "sanctions_hits",
    "alerts",
    "aggregates",
    "transactions",
    "customers",
]


def wipe_generated_data() -> dict:
    engine = create_engine(settings.core_db_url, future=True, pool_pre_ping=True)
    truncated: list[str] = []

    with engine.begin() as conn:
        for table in TABLES_TO_TRUNCATE:
            present = conn.execute(text("select to_regclass(:name)"), {"name": table}).scalar()
            if present is not None:
                truncated.append(table)

        if truncated:
            conn.execute(
                text(f"TRUNCATE TABLE {', '.join(truncated)} RESTART IDENTITY CASCADE")
            )

    return {"status": "ok", "truncated_tables": truncated}


def main() -> None:
    print(json.dumps(wipe_generated_data()))


if __name__ == "__main__":
    main()

