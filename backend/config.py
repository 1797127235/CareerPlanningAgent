"""Centralized configuration — single source of truth for env vars."""
import os
from pathlib import Path

# Load .env file if present
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.is_file():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path, override=False)
    except ImportError:
        pass  # python-dotenv not installed, rely on actual env vars

# ── LLM / DashScope ──────────────────────────────────────────────────────
DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY", "")
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

# ── Mem0 (Coach Memory) ──────────────────────────────────────────────────
MEM0_LLM_MODEL: str = os.getenv("MEM0_LLM_MODEL", "qwen-plus")
MEM0_EMBEDDING_MODEL: str = os.getenv("MEM0_EMBEDDING_MODEL", "text-embedding-v3")
MEM0_LLM_TEMPERATURE: float = float(os.getenv("MEM0_LLM_TEMPERATURE", "0.1"))

# ── Auth ─────────────────────────────────────────────────────────────────
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "career-planning-agent-dev-secret-change-in-prod")

# ── ResumeSDK (第三方简历解析) ────────────────────────────────────────────
# 阿里云市场: https://market.aliyun.com/detail/cmapi034316
#   BASE_URL = https://resumesdk.market.alicloudapi.com/ResumeParser
#   认证方式: APPCODE (购买后获得)
# SaaS 版: http://www.resumesdk.com/api/parse
#   认证方式: uid + pwd
RESUMESDK_ENABLED: bool = os.getenv("RESUMESDK_ENABLED", "true").lower() in ("1", "true", "yes")
RESUMESDK_APPCODE: str = os.getenv("RESUMESDK_APPCODE", "")
RESUMESDK_UID: str = os.getenv("RESUMESDK_UID", "")
RESUMESDK_PWD: str = os.getenv("RESUMESDK_PWD", "")
RESUMESDK_BASE_URL: str = os.getenv(
    "RESUMESDK_BASE_URL", "https://resumesdk.market.alicloudapi.com/ResumeParser"
)

# ── CORS ─────────────────────────────────────────────────────────────────
CORS_ORIGINS: list[str] = os.getenv(
    "CORS_ORIGINS", "http://localhost:5174,http://localhost:3000"
).split(",")
