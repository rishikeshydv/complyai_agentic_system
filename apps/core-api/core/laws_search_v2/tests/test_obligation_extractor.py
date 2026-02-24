from __future__ import annotations

from core.laws_search_v2.postprocess.chunker import DeterministicChunker
from core.laws_search_v2.postprocess.obligation_extractor import (
    ExtractionContext,
    GroundingValidator,
    MockLLMExtractor,
)


def test_mock_extractor_outputs_grounded_obligations(sample_document):
    chunker = DeterministicChunker()
    chunk = chunker.chunk_document(sample_document)[0]

    extractor = MockLLMExtractor()
    drafts = extractor.extract_obligations(
        chunk,
        ExtractionContext(
            jurisdiction=sample_document.jurisdiction,
            agency=sample_document.agency,
            instrument_type=sample_document.instrument_type,
        ),
    )

    assert drafts
    for draft in drafts:
        assert GroundingValidator.is_valid(chunk.text, draft.grounding, chunk.chunk_id)


def test_invalid_grounding_is_rejected(sample_document):
    chunker = DeterministicChunker()
    chunk = chunker.chunk_document(sample_document)[0]

    invalid_grounding = {
        "chunk_id": chunk.chunk_id,
        "span_start": 9999,
        "span_end": 10001,
    }
    assert GroundingValidator.is_valid(chunk.text, invalid_grounding, chunk.chunk_id) is False

    invalid_excerpt_grounding = {
        "chunk_id": chunk.chunk_id,
        "excerpt": "this sentence does not exist",
    }
    assert GroundingValidator.is_valid(chunk.text, invalid_excerpt_grounding, chunk.chunk_id) is False
