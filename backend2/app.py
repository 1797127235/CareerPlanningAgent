"""
backend2/app.py — FastAPI v2 application factory。

启动: uvicorn backend2.app:app --port 8001

依赖: backend2/core, backend2/db, backend2/routers（均独立）
       backend.models（唯一共享——同一数据库的 ORM 定义）
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend2.core.config import CORS_ORIGINS
from backend2.core.errors import AppError
from backend2.db.session import init_db

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s backend2.%(name)s - %(message)s",
    datefmt="%H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """v2 app lifecycle — init DB tables (idempotent)."""
    init_db()
    logger.info("backend2 started")
    yield


def create_app() -> FastAPI:
    """Build and return the v2 FastAPI application."""
    app = FastAPI(
        title="CareerOS API v2",
        version="2.0",
        lifespan=lifespan,
        redirect_slashes=False,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global error handler for AppError
    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "detail": exc.detail}},
        )

    # Routers
    from backend2.routers import health, profiles
    app.include_router(health.router, prefix="/api/v2", tags=["health"])
    app.include_router(profiles.router, prefix="/api/v2", tags=["profiles"])

    return app


app = create_app()
