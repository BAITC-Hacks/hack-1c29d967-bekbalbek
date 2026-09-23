import app.boot  # noqa: F401, I001

import logging
from collections.abc import Callable
from contextlib import asynccontextmanager

from agents import Model
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.health import router as health_router
from app.api.middleware import BodySizeLimitMiddleware
from app.api.runs import router as runs_router
from app.config import Settings, get_settings
from app.core.apply_service import ApplyService
from app.core.contracts import CaseNotFound
from app.core.errors import AppError
from app.core.events import EventBus
from app.core.llm import configure_model_provider, default_model_factory
from app.core.read_models import RunDTO
from app.core.run_registry import RunRegistry
from app.core.run_service import RunService, mark_interrupted_runs
from app.core.services import Services
from app.db.engine import configure_database, dispose_engine
from app.domain import DOMAIN

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    model_factory: Callable[[RunDTO], str | Model] | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        factory = session_factory or configure_database(settings.database_url)
        configure_model_provider(settings)
        bus = EventBus(factory)
        registry = RunRegistry()
        models = model_factory or default_model_factory(settings, DOMAIN)
        app.state.services = Services(
            settings=settings,
            session_factory=factory,
            bus=bus,
            registry=registry,
            run_service=RunService(factory, DOMAIN, settings, bus, models),
            apply_service=ApplyService(factory, DOMAIN, bus),
            domain=DOMAIN,
        )
        interrupted = await mark_interrupted_runs(factory, bus)
        if interrupted:
            logger.warning("marked %d in-flight run(s) as interrupted after restart", interrupted)
        yield
        await registry.cancel_all()
        if session_factory is None:
            await dispose_engine()

    app = FastAPI(title="Agent workspace", version=settings.app_version, lifespan=lifespan)
    app.add_middleware(BodySizeLimitMiddleware, exempt_prefixes=("/api/domain/meetings",))
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origin_list, allow_methods=["*"], allow_headers=["*"]
    )
    app.include_router(health_router)
    app.include_router(runs_router)
    if DOMAIN.api_router is not None:
        app.include_router(DOMAIN.api_router)

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_payload())

    @app.exception_handler(CaseNotFound)
    async def case_not_found_handler(_: Request, exc: CaseNotFound) -> JSONResponse:
        return JSONResponse(
            status_code=404, content={"error": {"code": "case_not_found", "message": str(exc), "details": {}}}
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        detail = (
            exc.detail
            if isinstance(exc.detail, dict) and "code" in exc.detail
            else {"code": "http_error", "message": str(exc.detail)}
        )
        return JSONResponse(status_code=exc.status_code, content={"error": {"details": {}, **detail}})

    return app


app = create_app()
