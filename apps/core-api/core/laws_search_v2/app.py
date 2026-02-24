from __future__ import annotations

import os

from fastapi import FastAPI

from .api.routes import build_law_router
from .db import SQLLawRepository
from .law_mapping.explainer import LLMExplainer, MockLLMExplainer
from .law_mapping.retrieval import IndexObligationRetriever, RepositoryObligationRetriever
from .law_mapping.service import LawMappingService
from .postprocess.indexers import ElasticsearchLawIndexer
from .search_service import LawSearchService


def create_app() -> FastAPI:
    app = FastAPI(title="Laws Search V2")

    repository = SQLLawRepository()

    use_es = str(os.getenv("LAWS_V2_USE_ES", str(settings.use_es))).strip().lower() in {"1", "true", "yes", "on"}
    indexer = ElasticsearchLawIndexer() if use_es else None

    llm_enabled = str(os.getenv("LAWS_V2_ENABLE_LLM", str(settings.enable_llm))).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    search_service = LawSearchService(repository=repository, indexer=indexer)

    retriever = IndexObligationRetriever(indexer=indexer) if indexer else RepositoryObligationRetriever(repository)
    explainer = LLMExplainer(llm_client=None) if llm_enabled else MockLLMExplainer()
    mapping_service = LawMappingService(
        repository=repository,
        retriever=retriever,
        explainer=explainer,
    )

    app.include_router(build_law_router(search_service, mapping_service))
    return app


app = create_app()
