"""解析策略 — 将 ResumeDocument 转为 ParseCandidate。"""
from __future__ import annotations

from backend2.services.profile.parser.strategies.llm_direct import LLMDirectStrategy
from backend2.services.profile.parser.strategies.resumesdk import ResumeSDKStrategy

__all__ = [
    "LLMDirectStrategy",
    "ResumeSDKStrategy",
]
