"""GET /api/v2/health — 存活检查 + 组件状态。"""
from __future__ import annotations

from fastapi import APIRouter

from sqlalchemy import text

from backend2.core.config import DASHSCOPE_API_KEY
from backend2.db.session import engine

router = APIRouter()


@router.get("/health")
def health():
    """返回 v2 服务存活状态和关键依赖可用性。"""
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    return {
        "status": "ok",
        "version": "2.0",
        "dependencies": {
            "db": "ok" if db_ok else "unavailable",
            "llm": "ok" if DASHSCOPE_API_KEY else "unconfigured",
        },
    }
