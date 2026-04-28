"""backend2 轻量 LLM 客户端。

提供与 backend/llm.py 一致的接口，使策略可直接迁移，无需修改 LLM 调用模式。
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

_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def _load_env() -> None:
    """加载项目根目录 .env 文件。"""
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        load_dotenv(env_path, override=True)
    except ImportError:
        pass


_load_env()


def _get_env(key: str, default: str = "") -> str:
    """读取环境变量，不存在时返回默认值。"""
    return os.getenv(key, default)


@lru_cache(maxsize=8)
def _cached_client(base_url: str, api_key: str, timeout: int):
    """返回按参数缓存的 OpenAI 客户端实例。"""
    from openai import OpenAI
    return OpenAI(base_url=base_url, api_key=api_key, timeout=timeout, max_retries=1)


def get_llm_client(timeout: int = 30):
    """返回配置好的 OpenAI 兼容客户端。

    环境变量:
        LLM_BASE_URL — 默认使用 DashScope 兼容端点
        DASHSCOPE_API_KEY — 必须；OPENAI_API_KEY 作为备选
    """
    base_url = _get_env("LLM_BASE_URL", _DEFAULT_BASE_URL)
    api_key = _get_env("DASHSCOPE_API_KEY") or _get_env("OPENAI_API_KEY") or "sk-placeholder"
    return _cached_client(base_url, api_key, timeout)


_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def parse_json_response(text: str) -> Any:
    """从文本中提取并解析第一个 JSON 对象或数组。

    处理以下格式：
    - 纯 JSON 字符串
    - Markdown 代码块（```json ... ```）
    - 前后夹杂文字说明的 JSON 块
    """
    if not text:
        return {}

    # 1. 尝试去除 markdown 代码块标记
    fence_match = _FENCE_RE.search(text)
    candidate = fence_match.group(1).strip() if fence_match else text.strip()

    # 2. 直接解析
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # 3. 定位首尾花括号/方括号再试
    for start_char, end_char in (("{", "}"), ("[", "]")):
        start = candidate.find(start_char)
        end = candidate.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(candidate[start : end + 1])
            except json.JSONDecodeError:
                continue

    logger.warning("parse_json_response: 无法从响应中提取 JSON（长度=%d）", len(text))
    return {}


def llm_chat(
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.7,
    timeout: int = 60,
) -> str:
    """同步 LLM 对话调用，带 tenacity 自动重试。

    对限流、超时、连接错误自动重试 3 次，指数退避：2s → 4s → 8s。

    返回:
        助手回复字符串；全部失败时返回空字符串。
    """
    try:
        from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
        import openai as _openai
    except ImportError:
        logger.error("tenacity 或 openai 未安装")
        return ""

    if model is None:
        model = _get_env("LLM_MODEL", "qwen-plus")

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
        logger.error("llm_chat 重试耗尽后仍失败 (model=%s): %s", model, exc)
        return ""
