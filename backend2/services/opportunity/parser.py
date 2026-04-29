"""backend2/services/opportunity/parser.py — JD 文本结构化提取。"""
from __future__ import annotations

import logging

from backend2.llm.client import llm_chat, parse_json_response
from backend2.schemas.opportunity import JDExtract
from backend2.services.opportunity.prompts import build_jd_parser_messages
from backend2.services.opportunity.sanitizer import sanitize_jd_text

logger = logging.getLogger(__name__)


def parse_jd(jd_text: str) -> JDExtract:
    """将 JD 原文解析为结构化 JDExtract。

    流程：
    1. 清洗 JD 文本（防 prompt injection）
    2. 调用 LLM 提取结构化信息
    3. 解析 JSON 响应
    4. 校验并返回 JDExtract

    LLM 调用失败或解析失败时返回空 JDExtract（各字段为默认值）。
    """
    # 1. 清洗
    cleaned = sanitize_jd_text(jd_text)
    if not cleaned or len(cleaned) < 10:
        logger.warning("JD 文本过短或清洗后为空: len=%d", len(cleaned))
        return JDExtract()

    # 2. 调用 LLM
    messages = build_jd_parser_messages(cleaned)
    try:
        raw = llm_chat(messages, temperature=0.3, timeout=60)
    except Exception:
        logger.exception("JD parser LLM 调用失败")
        return JDExtract()

    if not raw:
        logger.warning("JD parser LLM 返回空")
        return JDExtract()

    # 3. 解析 JSON
    try:
        data = parse_json_response(raw)
    except Exception:
        logger.exception("JD parser JSON 解析失败")
        return JDExtract()

    if not data:
        logger.warning("JD parser 无法从 LLM 响应解析 JSON")
        return JDExtract()

    # 4. 校验
    try:
        return JDExtract.model_validate(data)
    except Exception as exc:
        logger.warning("JD parser 校验失败: %s", exc)
        return JDExtract()
