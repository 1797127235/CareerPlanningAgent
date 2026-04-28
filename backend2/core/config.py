"""backend2/core/config.py — v2 独立配置，读取项目根 .env。"""
import os
from pathlib import Path

_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
if _ENV_PATH.is_file():
    try:
        from dotenv import load_dotenv
        load_dotenv(_ENV_PATH, override=False)
    except ImportError:
        pass

# ── LLM / DashScope ──────────────────────────────────────────────────────
DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY", "")
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

# ── Auth ─────────────────────────────────────────────────────────────────
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "career-planning-agent-dev-secret-change-in-prod")

# ── CORS ─────────────────────────────────────────────────────────────────
CORS_ORIGINS: list[str] = os.getenv(
    "CORS_ORIGINS", "http://localhost:5174,http://localhost:3000"
).split(",")

# ── ResumeSDK ────────────────────────────────────────────────────────────
RESUMESDK_ENABLED: bool = os.getenv("RESUMESDK_ENABLED", "true").lower() in ("true", "1", "yes")
RESUMESDK_APPCODE: str = os.getenv("RESUMESDK_APPCODE", "")
RESUMESDK_UID: str = os.getenv("RESUMESDK_UID", "")
RESUMESDK_PWD: str = os.getenv("RESUMESDK_PWD", "")
RESUMESDK_BASE_URL: str = os.getenv("RESUMESDK_BASE_URL", "https://www.resumesdk.com/api/parse")

# ── DB ───────────────────────────────────────────────────────────────────
DB_PATH: Path = Path(__file__).resolve().parent.parent.parent / "data" / "app_state" / "app.db"
