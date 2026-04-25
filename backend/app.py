"""
FastAPI application factory + lifespan.

Entry point: ``uvicorn backend.app:app``
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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import CORS_ORIGINS
from backend.db import init_db

# 把 skill 层的 logger.info('[skill:xxx] OK in X.Xs') 等也显示出来，
# 否则 uvicorn 默认 WARNING 级别会吞掉。
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    init_db()
    # Pre-warm Supervisor in background so server starts immediately
    def _prewarm():
        try:
            from agent.supervisor import _get_cached_supervisor
            _get_cached_supervisor()
            logger.info("Supervisor pre-warmed")
        except Exception as exc:
            logger.warning("Supervisor pre-warm skipped: %s", exc)

    threading.Thread(target=_prewarm, daemon=True).start()
    # Start interview reminder scheduler
    from backend.services.system.scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    yield
    stop_scheduler()


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    try:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.util import get_remote_address
        from slowapi.errors import RateLimitExceeded
        from slowapi.middleware import SlowAPIMiddleware
        _slowapi_available = True
    except ImportError:
        logger.warning("slowapi not installed — rate limiting disabled. Run: pip install slowapi")
        _slowapi_available = False

    app = FastAPI(
        title="职途智析 API",
        version="2.0",
        lifespan=lifespan,
        redirect_slashes=False,
    )

    if _slowapi_available:
        limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in CORS_ORIGINS],
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
        graph,
        growth_log,
        guidance,
        interview,
        jd,
        profiles,
        profiles_projects,
        profiles_sjt,
        recommendations,
        report,
    )

    app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
    app.include_router(applications.router, prefix="/api/applications", tags=["求职跟踪"])
    app.include_router(profiles.router, prefix="/api/profiles", tags=["画像"])
    app.include_router(profiles_projects.router, prefix="/api/profiles", tags=["画像"])
    app.include_router(profiles_sjt.router, prefix="/api/profiles", tags=["画像"])
    app.include_router(graph.router, prefix="/api/graph", tags=["图谱"])
    app.include_router(jd.router, prefix="/api/jd", tags=["JD诊断"])
    # 面试练习已砍 — 轻量校准改走 Coach 对话，不再需要独立 /practice 路由
    app.include_router(chat.router, prefix="/api/chat", tags=["AI对话"])
    app.include_router(report.router, prefix="/api/report", tags=["报告"])
    app.include_router(interview.router, prefix="/api/interview", tags=["模拟面试"])
    app.include_router(dashboard.router, prefix="/api/dashboard", tags=["看板"])
    app.include_router(guidance.router, prefix="/api/guidance", tags=["引导"])
    app.include_router(recommendations.router, prefix="/api/recommendations", tags=["推荐"])
    app.include_router(coach_results.router, prefix="/api/coach/results", tags=["教练结果"])
    app.include_router(growth_log.router, prefix="/api/growth-log", tags=["成长档案"])

    return app


app = create_app()
