from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from core.api.admin_routes import router as admin_router
from core.api.alerts_routes import router as alerts_router
from core.api.cases_routes import router as cases_router
from core.api.demo_routes import router as demo_router
from core.api.leads_routes import router as leads_router
from core.api.laws_v2_routes import router as laws_v2_router
from core.api.playground_routes import router as playground_router
from core.config import settings
from core.db.models import Base
from core.db.session import engine
from core.laws_search_v2.runtime import get_laws_v2_runtime
from core.logging_config import configure_logging
from core.utils.request_context import request_id_ctx

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    docs_url="/v1/docs",
    redoc_url="/v1/redoc",
    openapi_url="/v1/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(alerts_router)
app.include_router(cases_router)
app.include_router(demo_router)
app.include_router(leads_router)
app.include_router(admin_router)
app.include_router(playground_router)
app.include_router(laws_v2_router)
app.include_router(get_laws_v2_runtime().router)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    token = request_id_ctx.set(request_id)
    try:
        response = await call_next(request)
    finally:
        request_id_ctx.reset(token)
    response.headers["X-Request-ID"] = request_id
    return response


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    runtime = get_laws_v2_runtime()
    logger.info(
        "core_startup",
        extra={
            "service": settings.app_name,
            "laws_v2_runtime_ready": runtime.ready,
            "laws_v2_use_es": runtime.use_es,
            "laws_v2_error": runtime.error,
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
