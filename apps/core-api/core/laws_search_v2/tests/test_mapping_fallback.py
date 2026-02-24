from __future__ import annotations

from core.laws_search_v2.db import InMemoryLawRepository
from core.laws_search_v2.law_mapping.explainer import MockLLMExplainer
from core.laws_search_v2.law_mapping.models import Event
from core.laws_search_v2.law_mapping.retrieval import IndexObligationRetriever
from core.laws_search_v2.law_mapping.service import LawMappingService
from core.laws_search_v2.postprocess.indexers import InMemoryLawIndexer
from core.laws_search_v2.postprocess.postprocessor import PostProcessor


def test_fallback_mapping_returns_grounded_explanations(sample_document):
    repo = InMemoryLawRepository()
    repo.add_document(sample_document)

    indexer = InMemoryLawIndexer()
    processor = PostProcessor(repository=repo, indexer=indexer)
    processor.process_documents(docs=[sample_document])

    service = LawMappingService(
        repository=repo,
        retriever=IndexObligationRetriever(indexer=indexer),
        explainer=MockLLMExplainer(),
    )

    event = Event(
        bank_id="bank_999",
        event_id="alert-fallback-1",
        event_type="SANCTIONS_ALERT",
        rule_triggered="RULE_OFAC_NAME_MATCH",
        rule_description="Potential OFAC name match on beneficiary.",
        conditions_triggered=[
            {
                "field": "ofac_name_similarity",
                "operator": ">=",
                "threshold": 0.9,
                "actual": 0.95,
                "window_days": 1,
            }
        ],
        jurisdiction_context="federal + NJ",
    )

    result = service.map_event(event)

    assert result.mapping_mode == "fallback"
    assert result.obligations
    assert result.citations

    for citation in result.citations:
        assert "condition[" in citation.why_relevant
        assert "grounding(chunk_id=" in citation.why_relevant

    assert repo.proposed_maps
