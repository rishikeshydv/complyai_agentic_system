from __future__ import annotations

from fastapi import APIRouter

from ..law_mapping.models import Event, MappingResult
from ..law_mapping.service import LawMappingService
from ..search_service import LawSearchService


def build_law_router(
    search_service: LawSearchService,
    mapping_service: LawMappingService,
) -> APIRouter:
    router = APIRouter(prefix="/v1/laws", tags=["laws-v2"])

    @router.get("/search")
    def search_laws(
        q: str,
        jurisdiction: str | None = None,
        agency: str | None = None,
        type: str | None = None,
    ):
        return search_service.search(
            query=q,
            jurisdiction=jurisdiction,
            agency=agency,
            instrument_type=type,
        )

    @router.post("/map-event", response_model=MappingResult)
    def map_event(event: Event) -> MappingResult:
        return mapping_service.map_event(event)

    return router
