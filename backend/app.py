"""
FastAPI application factory + lifespan.

Entry point: ``uvicorn backend.app:app``
"""
from __future__ import annotations

import logging
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    init_db()
    # Pre-warm Supervisor in background so server starts immediately
    def _prewarm():
        try:
            from backend.routers.chat import _get_supervisor
            _get_supervisor()
            logger.info("Supervisor pre-warmed")
        except Exception as exc:
            logger.warning("Supervisor pre-warm skipped: %s", exc)

    threading.Thread(target=_prewarm, daemon=True).start()
    # Start interview reminder scheduler
    from backend.services.reminder_service import start_scheduler, stop_scheduler
    start_scheduler()
    yield
    stop_scheduler()


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware

    limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

    app = FastAPI(
        title="职途智析 API",
        version="2.0",
        lifespan=lifespan,
        redirect_slashes=False,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    _cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in _cors_origins],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from backend.routers import (
        applications,
        auth,
        chat,
        coach_results,
        dashboard,
        extension,
        graph,
        growth_log,
        guidance,
        jd,
        practice,
        profiles,
        recommendations,
        report,
    )

    app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
    app.include_router(applications.router, prefix="/api/applications", tags=["求职跟踪"])
    app.include_router(profiles.router, prefix="/api/profiles", tags=["画像"])
    app.include_router(graph.router, prefix="/api/graph", tags=["图谱"])
    app.include_router(jd.router, prefix="/api/jd", tags=["JD诊断"])
    app.include_router(extension.router, prefix="/api/extension", tags=["浏览器扩展"])
    app.include_router(practice.router, prefix="/api/practice", tags=["面试训练"])
    app.include_router(chat.router, prefix="/api/chat", tags=["AI对话"])
    app.include_router(report.router, prefix="/api/report", tags=["报告"])
    app.include_router(dashboard.router, prefix="/api/dashboard", tags=["看板"])
    app.include_router(guidance.router, prefix="/api/guidance", tags=["引导"])
    app.include_router(recommendations.router, prefix="/api/recommendations", tags=["推荐"])
    app.include_router(coach_results.router, prefix="/api/coach/results", tags=["教练结果"])
    app.include_router(growth_log.router, prefix="/api/growth-log", tags=["成长档案"])

    return app


app = create_app()
