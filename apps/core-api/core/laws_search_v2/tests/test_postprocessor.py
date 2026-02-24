from __future__ import annotations

from core.laws_search_v2.db import InMemoryLawRepository
from core.laws_search_v2.postprocess.indexers import InMemoryLawIndexer
from core.laws_search_v2.postprocess.postprocessor import PostProcessor


def test_postprocessor_creates_chunks_and_obligations(sample_document):
    repo = InMemoryLawRepository()
    repo.add_document(sample_document)
    indexer = InMemoryLawIndexer()
    processor = PostProcessor(repository=repo, indexer=indexer)

    stats = processor.process_documents(docs=[sample_document])

    assert stats["processed_documents"] == 1
    assert stats["chunks_upserted"] > 0
    assert stats["obligations_upserted"] > 0

    assert len(repo.chunks) > 0
    assert len(repo.obligations) > 0
    assert len(indexer.chunk_docs) > 0
    assert len(indexer.obligation_docs) > 0
