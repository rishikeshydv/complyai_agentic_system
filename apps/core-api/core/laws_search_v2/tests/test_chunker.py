from __future__ import annotations

from core.laws_search_v2.postprocess.chunker import DeterministicChunker


def test_chunker_produces_deterministic_chunk_ids(sample_document):
    chunker = DeterministicChunker()

    first = chunker.chunk_document(sample_document)
    second = chunker.chunk_document(sample_document)

    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]


def test_chunker_non_empty_text_and_stable_hash(sample_document):
    chunker = DeterministicChunker()
    chunks = chunker.chunk_document(sample_document)

    assert chunks
    for chunk in chunks:
        assert chunk.text.strip() != ""
        assert len(chunk.chunk_hash) == 64

    rerun = chunker.chunk_document(sample_document)
    assert [chunk.chunk_hash for chunk in chunks] == [chunk.chunk_hash for chunk in rerun]
