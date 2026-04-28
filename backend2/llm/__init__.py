"""backend2 LLM 客户端 — 轻量 OpenAI 兼容封装。"""
from __future__ import annotations

from backend2.llm.client import get_llm_client, llm_chat, parse_json_response

__all__ = [
    "get_llm_client",
    "llm_chat",
    "parse_json_response",
]
