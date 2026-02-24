from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request

from connector.api.routes import router as bank_router
from connector.api.routes import sim_router
from connector.config import settings
from connector.db.migrate import ensure_bank_id_columns
from connector.db.models import Base
from connector.db.session import engine
from connector.logging_config import configure_logging
from connector.services.simulator import simulator_engine
from connector.utils.request_context import request_id_ctx

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)
app.include_router(bank_router)
app.include_router(sim_router)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
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
    ensure_bank_id_columns(engine)
    simulator_engine.ensure_thread_started()
    logger.info("connector_startup", extra={"service": settings.app_name})


@app.on_event("shutdown")
def shutdown() -> None:
    simulator_engine.shutdown()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
