"""Centralized configuration — single source of truth for env vars."""
import os

# ── LLM / DashScope ──────────────────────────────────────────────────────
DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY", "")
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
DASHSCOPE_BASE_URL: str = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

# ── Mem0 (Coach Memory) ──────────────────────────────────────────────────
MEM0_LLM_MODEL: str = os.getenv("MEM0_LLM_MODEL", "qwen-plus")
MEM0_EMBEDDING_MODEL: str = os.getenv("MEM0_EMBEDDING_MODEL", "text-embedding-v3")
MEM0_LLM_TEMPERATURE: float = float(os.getenv("MEM0_LLM_TEMPERATURE", "0.1"))

# ── Auth ─────────────────────────────────────────────────────────────────
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "career-planning-agent-dev-secret-change-in-prod")

# ── CORS ─────────────────────────────────────────────────────────────────
CORS_ORIGINS: list[str] = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")
