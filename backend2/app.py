"""
backend2/app.py — FastAPI v2 application factory，同时也是统一运行时入口。

启动: uvicorn backend2.app:app --port 8000

职责:
- 原生 v2 路由挂载在 /api/v2
- 临时兼容层：直接挂载 legacy backend 路由在 /api，保证前端零改动过渡
- 最终目标：逐步将 /api/* 路由真正迁移到 backend2/routers/* 下
"""
from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
except ImportError:
    pass

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend2.core.config import CORS_ORIGINS
from backend2.core.errors import AppError
from backend2.db.session import init_db as init_db_v2

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s backend2.%(name)s - %(message)s",
    datefmt="%H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Unified app lifecycle."""
    # Init DB tables via backend2 engine (idempotent, same SQLite file)
    init_db_v2()

    # Prewarm Supervisor in background (same as legacy backend)
    def _prewarm():
        try:
            from agent.supervisor import _get_cached_supervisor
            _get_cached_supervisor()
            logger.info("Supervisor pre-warmed")
        except Exception as exc:
            logger.warning("Supervisor pre-warm skipped: %s", exc)

    threading.Thread(target=_prewarm, daemon=True).start()

    # Start interview reminder scheduler (same as legacy backend)
    from backend.services.system.scheduler import start_scheduler, stop_scheduler
    start_scheduler()

    logger.info("backend2 unified runtime started")
    yield

    stop_scheduler()


def create_app() -> FastAPI:
    """Build and return the unified FastAPI application."""
    app = FastAPI(
        title="CareerOS API",
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

    # Global error handler for AppError (v2 style)
    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "detail": exc.detail}},
        )

    # ── Native v2 routers ────────────────────────────────────────────
    from backend2.routers import health, profiles, opportunity
    app.include_router(health.router, prefix="/api/v2", tags=["health"])
    app.include_router(profiles.router, prefix="/api/v2", tags=["profiles"])
    app.include_router(opportunity.router, prefix="/api/v2", tags=["opportunities"])

    # ── Migrated legacy routes (backend2 native ownership) ───────────
    from backend2.routers import (
        applications,
        auth,
        chat,
        coach_results,
        dashboard,
        graph,
        growth_log,
        guidance,
        interview,
        jd,
        profiles_legacy,
        profiles_projects,
        profiles_sjt,
        recommendations,
        report,
    )

    app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
    app.include_router(applications.router, prefix="/api/applications", tags=["求职跟踪"])
    app.include_router(profiles_legacy.router, prefix="/api/profiles", tags=["画像"])
    app.include_router(profiles_projects.router, prefix="/api/profiles", tags=["画像"])
    app.include_router(profiles_sjt.router, prefix="/api/profiles", tags=["画像"])
    app.include_router(graph.router, prefix="/api/graph", tags=["图谱"])
    app.include_router(jd.router, prefix="/api/jd", tags=["JD诊断"])
    app.include_router(chat.router, prefix="/api/chat", tags=["AI对话"])
    app.include_router(report.router, prefix="/api/report", tags=["报告"])
    app.include_router(interview.router, prefix="/api/interview", tags=["模拟面试"])
    app.include_router(dashboard.router, prefix="/api/dashboard", tags=["看板"])
    app.include_router(guidance.router, prefix="/api/guidance", tags=["引导"])
    app.include_router(recommendations.router, prefix="/api/recommendations", tags=["推荐"])
    app.include_router(coach_results.router, prefix="/api/coach/results", tags=["教练结果"])
    app.include_router(growth_log.router, prefix="/api/growth-log", tags=["成长档案"])

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
