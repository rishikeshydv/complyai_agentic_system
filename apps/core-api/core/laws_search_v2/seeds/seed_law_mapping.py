from __future__ import annotations

import uuid

from core.laws_search_v2.db import create_sql_repository
from core.laws_search_v2.law_mapping.models import ControlObjective, ControlToObligationMap, RuleToTypologyMap, Typology


def main() -> int:
    repo = create_sql_repository()

    repo.upsert_control_objective(
        ControlObjective(
            control_id="CTRL_SAR_FILE",
            name="SAR Filing",
            description="File suspicious activity reports when required.",
            expected_artifacts=["SAR filing", "case narrative"],
            jurisdiction_scope="federal",
        )
    )
    repo.upsert_control_objective(
        ControlObjective(
            control_id="CTRL_STRUCTURING_MONITOR",
            name="Structuring Monitoring",
            description="Detect and escalate potential structuring.",
            expected_artifacts=["alert logs", "investigation notes"],
            jurisdiction_scope="both",
        )
    )
    repo.upsert_control_objective(
        ControlObjective(
            control_id="CTRL_OFAC_SCREEN",
            name="OFAC Screening",
            description="Screen customers and counterparties against OFAC lists.",
            expected_artifacts=["screening logs", "hit disposition notes"],
            jurisdiction_scope="both",
        )
    )

    repo.upsert_typology(
        Typology(
            typology_id="TYPO_STRUCTURING",
            name="Structuring",
            signals_definition={"signals": ["cash deposits below threshold", "rapid sequential deposits"]},
            default_control_ids=["CTRL_STRUCTURING_MONITOR", "CTRL_SAR_FILE"],
        )
    )
    repo.upsert_typology(
        Typology(
            typology_id="TYPO_OFAC_NAME_MATCH",
            name="OFAC Name Match",
            signals_definition={"signals": ["sanctions name similarity", "blocked-party match"]},
            default_control_ids=["CTRL_OFAC_SCREEN"],
        )
    )

    repo.upsert_rule_map(
        RuleToTypologyMap(
            id=uuid.UUID("11111111-1111-4111-8111-111111111111"),
            bank_id="bank_demo",
            rule_triggered="RULE_STRUCTURING_001",
            typology_id="TYPO_STRUCTURING",
            control_ids=["CTRL_STRUCTURING_MONITOR", "CTRL_SAR_FILE"],
            confidence=0.95,
            version="2026-02-08",
            owner="seed",
        )
    )
    repo.upsert_rule_map(
        RuleToTypologyMap(
            id=uuid.UUID("22222222-2222-4222-8222-222222222222"),
            bank_id="bank_demo",
            rule_triggered="RULE_OFAC_NAME_MATCH",
            typology_id="TYPO_OFAC_NAME_MATCH",
            control_ids=["CTRL_OFAC_SCREEN"],
            confidence=0.97,
            version="2026-02-08",
            owner="seed",
        )
    )

    sar_rows = repo.search_obligations_text("suspicious activity report", top_k=20)

    ofac_rows = repo.search_obligations_text("OFAC sanctions screen", top_k=20)
    if not ofac_rows:
        ofac_rows = repo.search_obligations_text("ofac", top_k=20)
    if not ofac_rows:
        ofac_rows = repo.search_obligations_text("sanctions", top_k=20)

    sar_obligation_ids = [uuid.UUID(str(row["obligation_id"])) for row in sar_rows if row.get("obligation_id")]
    ofac_obligation_ids = [uuid.UUID(str(row["obligation_id"])) for row in ofac_rows if row.get("obligation_id")]

    # Preserve order and remove duplicates.
    sar_obligation_ids = list(dict.fromkeys(sar_obligation_ids))
    ofac_obligation_ids = list(dict.fromkeys(ofac_obligation_ids))

    repo.upsert_control_to_obligation_map(
        ControlToObligationMap(
            id=uuid.UUID("33333333-3333-4333-8333-333333333333"),
            control_id="CTRL_SAR_FILE",
            obligation_ids=sar_obligation_ids,
            jurisdiction_filter="federal",
            priority=10,
        )
    )
    repo.upsert_control_to_obligation_map(
        ControlToObligationMap(
            id=uuid.UUID("44444444-4444-4444-8444-444444444444"),
            control_id="CTRL_STRUCTURING_MONITOR",
            obligation_ids=sar_obligation_ids,
            jurisdiction_filter="both",
            priority=8,
        )
    )
    repo.upsert_control_to_obligation_map(
        ControlToObligationMap(
            id=uuid.UUID("55555555-5555-4555-8555-555555555555"),
            control_id="CTRL_OFAC_SCREEN",
            obligation_ids=ofac_obligation_ids,
            jurisdiction_filter="both",
            priority=10,
        )
    )

    print(
        {
            "sar_obligation_count": len(sar_obligation_ids),
            "ofac_obligation_count": len(ofac_obligation_ids),
            "status": "ok",
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
