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

# 防御性加载 .env，避免 import 顺序导致读不到环境变量
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"), override=False)

logger = logging.getLogger(__name__)

_memory: Optional[Memory] = None


def _build_config() -> dict:
    """构造 Mem0 配置。DashScope 作为 LLM + Embedding provider。"""
    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    llm_model = os.getenv("MEM0_LLM_MODEL", "qwen-plus")
    embedding_model = os.getenv("MEM0_EMBEDDING_MODEL", "text-embedding-v3")
    try:
        temperature = float(os.getenv("MEM0_LLM_TEMPERATURE", "0.1"))
    except ValueError:
        temperature = 0.1

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


def search_user_context(user_id: int, query: str, limit: int = 5) -> list[str]:
    """按语义搜索用户相关记忆。供 supervisor 按 agent 需求切片注入。"""
    try:
        mem = get_memory()
        results = mem.search(query=query, user_id=str(user_id), limit=limit)
        # Mem0 返回结构: [{"memory": "...", "score": 0.x, ...}, ...]
        return [r.get("memory", "") for r in results if isinstance(r, dict)]
    except Exception:
        logger.exception("Memory search failed for user %d", user_id)
        return []


def get_all_memories(user_id: int) -> list[str]:
    """拿该用户的全部记忆（用于冷启动注入）。"""
    try:
        mem = get_memory()
        results = mem.get_all(user_id=str(user_id))
        return [r.get("memory", "") for r in results if isinstance(r, dict)]
    except Exception:
        logger.exception("get_all_memories failed for user %d", user_id)
        return []


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
