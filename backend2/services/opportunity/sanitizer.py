"""backend2/services/opportunity/sanitizer.py — JD 文本清洗，防御 prompt injection。"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_INJECTION_PATTERNS = [
    re.compile(r"```\s*(?:system|instructions?|ignore|override).*?```", re.IGNORECASE | re.DOTALL),
    re.compile(r"ignore\s+(?:all\s+)?(?:previous|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"forget\s+(?:all\s+)?(?:previous|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:a|an)\s+", re.IGNORECASE),
    re.compile(r"disregard\s+(?:the\s+)?(?:previous|above)\s+instructions?", re.IGNORECASE),
]

_MAX_JD_LENGTH = 15000


def sanitize_jd_text(text: str, max_length: int = _MAX_JD_LENGTH) -> str:
    """清洗 JD 文本。

    - 截断过长文本（默认 15KB，约 5000 汉字）
    - 移除常见 prompt injection 标记
    - 保留正常 JD 内容
    """
    if not text:
        return ""

    text = text.strip()

    # 截断
    if len(text) > max_length:
        logger.info("JD 文本过长，截断至 %d 字符", max_length)
        text = text[:max_length]

    # 清洗 injection
    original_text = text
    for pattern in _INJECTION_PATTERNS:
        text = pattern.sub("[BLOCKED]", text)

    if text != original_text:
        logger.warning("JD 文本中发现并移除可疑内容")

    return text.strip()
