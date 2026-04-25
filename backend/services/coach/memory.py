"""Coach 记忆层 — 封装 Mem0，对外提供 add/search/get_user_context 接口。

配置：
- LLM: DashScope (OpenAI-compatible endpoint)
- Embedding: DashScope text-embedding-v3
- 存储: 本地 Qdrant embedded 模式
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from mem0 import Memory

from backend.config import (
    DASHSCOPE_API_KEY,
    LLM_BASE_URL,
    MEM0_EMBEDDING_MODEL,
    MEM0_LLM_MODEL,
    MEM0_LLM_TEMPERATURE,
)

# 防御性加载 .env，避免 import 顺序导致读不到环境变量
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"), override=False)

logger = logging.getLogger(__name__)

_memory: Optional[Memory] = None


def _build_config() -> dict:
    """构造 Mem0 配置。DashScope 作为 LLM + Embedding provider。"""
    api_key = DASHSCOPE_API_KEY
    base_url = LLM_BASE_URL
    llm_model = MEM0_LLM_MODEL
    embedding_model = MEM0_EMBEDDING_MODEL
    temperature = MEM0_LLM_TEMPERATURE

    return {
        "llm": {
            "provider": "openai",
            "config": {
                "model": llm_model,
                "api_key": api_key,
                "openai_base_url": base_url,
                "temperature": temperature,
            }
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": embedding_model,
                "api_key": api_key,
                "openai_base_url": base_url,
            }
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "coach_memory",
                "path": "./data/mem0_qdrant",  # 本地 embedded 模式
            }
        },
    }


def get_memory() -> Memory:
    """Lazy init Mem0 实例（进程级单例）。"""
    global _memory
    if _memory is None:
        try:
            _memory = Memory.from_config(_build_config())
            logger.info("Mem0 initialized with DashScope")
        except Exception:
            logger.exception("Mem0 init failed")
            raise
    return _memory


def add_conversation(user_id: int, conversation: str) -> None:
    """从对话中抽取记忆（Mem0 自动做 LLM extraction + 去重 + 冲突处理）。"""
    try:
        mem = get_memory()
        mem.add(conversation, user_id=str(user_id))
    except Exception:
        logger.exception("Failed to add memory for user %d", user_id)


def migrate_legacy_memo(user_id: int, legacy_text: str) -> None:
    """一次性迁移：把老的 coach_memo 字符串塞进 Mem0。幂等（Mem0 内部去重）。"""
    if not legacy_text or not legacy_text.strip():
        return
    try:
        mem = get_memory()
        mem.add(f"[历史备忘录] {legacy_text}", user_id=str(user_id))
        logger.info("Migrated legacy memo for user %d (len=%d)", user_id, len(legacy_text))
    except Exception:
        logger.exception("Legacy memo migration failed for user %d", user_id)
