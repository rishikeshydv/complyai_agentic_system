from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from .api.routes import build_law_router
from .config import settings
from .db import InMemoryLawRepository, SQLLawRepository
from .law_mapping.explainer import LLMExplainer, MockLLMExplainer
from .law_mapping.retrieval import RepositoryObligationRetriever
from .law_mapping.service import LawMappingService
from .postprocess.indexers import ElasticsearchLawIndexer, LawIndexer
from .search_service import LawSearchService


class NoopLawIndexer:
    def ensure_indices(self) -> None:
        return

    def index_chunks(self, chunks: list[Any], docs_by_id: dict[Any, Any]) -> tuple[int, int]:
        return 0, 0

    def index_obligations(
        self,
        obligations: list[Any],
        chunks_by_id: dict[str, Any],
        docs_by_id: dict[Any, Any],
    ) -> tuple[int, int]:
        return 0, 0

    def search_obligations(
        self,
        query: str,
        top_k: int,
        jurisdiction: str | None = None,
        agency: str | None = None,
        instrument_type: str | None = None,
    ) -> list[dict[str, Any]]:
        return []


@dataclass(frozen=True)
class LawsV2Runtime:
    router: Any
    repository: Any
    search_service: LawSearchService
    mapping_service: LawMappingService
    indexer: LawIndexer
    use_es: bool
    ready: bool
    error: str | None = None


@lru_cache
def get_laws_v2_runtime() -> LawsV2Runtime:
    try:
        repository = SQLLawRepository(database_url=settings.database_url)
        indexer: LawIndexer
        use_es = settings.use_es
        if use_es:
            indexer = ElasticsearchLawIndexer(
                chunks_index=settings.es_chunks_index,
                obligations_index=settings.es_obligations_index,
            )
        else:
            indexer = NoopLawIndexer()

        search_service = LawSearchService(repository=repository, indexer=indexer if use_es else None)
        explainer = LLMExplainer(llm_client=None) if settings.enable_llm else MockLLMExplainer()
        mapping_service = LawMappingService(
            repository=repository,
            retriever=RepositoryObligationRetriever(repository),
            explainer=explainer,
        )
        router = build_law_router(search_service=search_service, mapping_service=mapping_service)

        return LawsV2Runtime(
            router=router,
            repository=repository,
            search_service=search_service,
            mapping_service=mapping_service,
            indexer=indexer,
            use_es=use_es,
            ready=True,
            error=None,
        )
    except Exception as exc:
        repository = InMemoryLawRepository()
        search_service = LawSearchService(repository=repository, indexer=None)
        mapping_service = LawMappingService(
            repository=repository,
            retriever=RepositoryObligationRetriever(repository),
            explainer=MockLLMExplainer(),
        )
        router = build_law_router(search_service=search_service, mapping_service=mapping_service)
        return LawsV2Runtime(
            router=router,
            repository=repository,
            search_service=search_service,
            mapping_service=mapping_service,
            indexer=NoopLawIndexer(),
            use_es=False,
            ready=False,
            error=str(exc),
        )
