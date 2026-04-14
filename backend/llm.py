"""
backend/llm.py — LLM client utilities.

Provides a cached OpenAI-compatible client (DashScope), env helpers, and
lightweight JSON parsing / chat helpers.

Moved from agent/llm.py to eliminate backend→agent reverse dependency.
"""
from __future__ import annotations

import json
import logging
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── .env loading ────────────────────────────────────────────────────────────

def _load_env() -> None:
    """Load .env from project root (silent if file not found or dotenv not installed)."""
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).resolve().parent.parent / ".env"
        load_dotenv(env_path, override=True)
    except ImportError:
        pass  # python-dotenv is optional


_load_env()


# ── Env helpers ─────────────────────────────────────────────────────────────

def get_env_str(key: str, default: str = "") -> str:
    """Read a string env var, falling back to *default*."""
    return os.getenv(key, default)


def get_env_int(key: str, default: int = 0) -> int:
    """Read an integer env var, falling back to *default* on missing / invalid values."""
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Env var %s=%r is not a valid integer; using default %d", key, raw, default)
        return default


# ── LLM client ──────────────────────────────────────────────────────────────

_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

@lru_cache(maxsize=8)
def _cached_client(base_url: str, api_key: str, timeout: int):
    """Return a cached OpenAI client keyed by (base_url, api_key, timeout)."""
    from openai import OpenAI
    return OpenAI(base_url=base_url, api_key=api_key, timeout=timeout, max_retries=1)


def get_llm_client(timeout: int = 30):
    """Return a cached OpenAI-compatible client configured from environment.

    Env vars:
        LLM_BASE_URL     — defaults to DashScope compatible endpoint
        DASHSCOPE_API_KEY — required for DashScope; OPENAI_API_KEY as fallback
    """
    base_url = get_env_str("LLM_BASE_URL", _DEFAULT_BASE_URL)
    api_key = (
        get_env_str("DASHSCOPE_API_KEY")
        or get_env_str("OPENAI_API_KEY")
        or "sk-placeholder"
    )
    return _cached_client(base_url, api_key, timeout)


# ── Model name lookup ────────────────────────────────────────────────────────

_MODEL_MAP: dict[str, str] = {
    "fast": "qwen3.6-plus",
    "strong": "qwen-max",
    "router": "qwen3.6-plus",
    "default": "qwen3.6-plus",
}


def get_model(purpose: str = "default") -> str:
    """Return model name for a given purpose ('fast', 'strong', 'router', 'default').

    Falls back to the LLM_MODEL env var if set, otherwise uses the built-in map.
    """
    env_override = get_env_str("LLM_MODEL")
    if env_override:
        return env_override
    return _MODEL_MAP.get(purpose, _MODEL_MAP["default"])


# ── LangChain ChatOpenAI factory ─────────────────────────────────────────────

def get_chat_model(temperature: float = 0.3, timeout: int = 30, purpose: str = "default"):
    """Return a configured ChatOpenAI instance for LangChain agents.

    Centralizes model name, API key, base URL, timeout, and retry config
    so agent files don't duplicate this logic.
    """
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=get_model(purpose),
        api_key=(
            get_env_str("DASHSCOPE_API_KEY")
            or get_env_str("OPENAI_API_KEY")
            or "sk-placeholder"
        ),
        base_url=get_env_str("LLM_BASE_URL", _DEFAULT_BASE_URL),
        temperature=temperature,
        request_timeout=timeout,
        max_retries=1,
        streaming=True,
        stream_usage=False,
    )


# ── JSON response parsing ────────────────────────────────────────────────────

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def parse_json_response(text: str) -> Any:
    """Extract and parse the first JSON object or array from *text*.

    Handles:
    - Raw JSON strings
    - Markdown code fences (```json ... ```)
    - Leading/trailing prose around the JSON block
    """
    if not text:
        return {}

    # 1. Try to strip markdown fences
    fence_match = _FENCE_RE.search(text)
    candidate = fence_match.group(1).strip() if fence_match else text.strip()

    # 2. Try direct parse
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # 3. Locate first { or [ and try from there
    for start_char, end_char in (("{", "}"), ("[", "]")):
        start = candidate.find(start_char)
        end = candidate.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(candidate[start : end + 1])
            except json.JSONDecodeError:
                continue

    logger.warning("parse_json_response: could not extract JSON from response (len=%d)", len(text))
    return {}


# ── Simple sync chat ─────────────────────────────────────────────────────────

def llm_chat(
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.7,
    timeout: int = 60,
) -> str:
    """Simple synchronous chat call with automatic retry (tenacity).

    Retries up to 3 times on transient errors (rate limits, network issues)
    with exponential backoff: 2s → 4s → 8s.

    Returns:
        Assistant reply as a plain string (empty string on all failures).
    """
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    import openai as _openai

    if model is None:
        model = get_model("default")

    client = get_llm_client(timeout=timeout)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((
            _openai.RateLimitError,
            _openai.APITimeoutError,
            _openai.APIConnectionError,
        )),
        reraise=False,
    )
    def _call() -> str:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        return resp.choices[0].message.content or ""

    try:
        return _call()
    except Exception as exc:
        logger.error("llm_chat failed after retries (model=%s): %s", model, exc)
        return ""


# ── Backward-compat aliases ──

load_env = _load_env
