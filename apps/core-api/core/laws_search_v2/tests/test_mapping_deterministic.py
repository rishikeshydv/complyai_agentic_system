from __future__ import annotations

import uuid

from core.laws_search_v2.db import InMemoryLawRepository
from core.laws_search_v2.law_mapping.models import ControlObjective, ControlToObligationMap, Event, RuleToTypologyMap, Typology
from core.laws_search_v2.law_mapping.service import LawMappingService
from core.laws_search_v2.postprocess.indexers import InMemoryLawIndexer
from core.laws_search_v2.postprocess.postprocessor import PostProcessor


def test_deterministic_mapping_returns_seeded_obligations(sample_document):
    repo = InMemoryLawRepository()
    repo.add_document(sample_document)

    processor = PostProcessor(repository=repo, indexer=InMemoryLawIndexer())
    processor.process_documents(docs=[sample_document])

    seeded_obligation_ids = list(repo.obligations.keys())
    assert seeded_obligation_ids

    repo.upsert_control_objective(
        ControlObjective(
            control_id="CTRL_SAR_001",
            name="SAR Filing Control",
            description="Ensure suspicious activity is reported.",
            expected_artifacts=["SAR filing"],
            jurisdiction_scope="federal",
        )
    )
    repo.upsert_typology(
        Typology(
            typology_id="TYPO_STRUCTURING",
            name="Structuring",
            signals_definition={"signal": "cash structuring"},
            default_control_ids=["CTRL_SAR_001"],
        )
    )
    repo.upsert_rule_map(
        RuleToTypologyMap(
            id=uuid.uuid4(),
            bank_id="bank_123",
            rule_triggered="RULE_STRUCTURING_001",
            typology_id="TYPO_STRUCTURING",
            control_ids=None,
            confidence=0.9,
            version="2026-02-08",
            owner="compliance",
        )
    )
    repo.upsert_control_to_obligation_map(
        ControlToObligationMap(
            id=uuid.uuid4(),
            control_id="CTRL_SAR_001",
            obligation_ids=seeded_obligation_ids,
            jurisdiction_filter="federal",
            priority=10,
        )
    )

    service = LawMappingService(repository=repo)

    event = Event(
        bank_id="bank_123",
        event_id="alert-1",
        event_type="AML_ALERT",
        rule_triggered="RULE_STRUCTURING_001",
        rule_description="Potential structuring under reporting threshold.",
        conditions_triggered=[
            {
                "field": "cash_deposit_count_7d",
                "operator": ">=",
                "threshold": 3,
                "actual": 5,
                "window_days": 7,
            }
        ],
        jurisdiction_context="federal + NJ",
    )

    result = service.map_event(event)

    assert result.mapping_mode == "deterministic"
    assert result.controls
    assert result.obligations
    assert result.citations
    assert any("grounding(chunk_id=" in citation.why_relevant for citation in result.citations)
