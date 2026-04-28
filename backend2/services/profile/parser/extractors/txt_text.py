"""纯文本提取器 — 处理 .txt、.md 及任何可用 UTF-8 解码的文件。"""
from __future__ import annotations

from backend2.schemas.profile import ResumeDocument
from backend2.services.profile.parser.base import TextExtractor


class TxtTextExtractor(TextExtractor):
    """尽力 UTF-8 解码纯文本文件。"""

    name = "txt"

    def supports(self, filename: str, content_type: str | None) -> bool:
        fn = filename.lower()
        return fn.endswith(".txt") or fn.endswith(".md") or content_type == "text/plain"

    def extract(self, file_bytes: bytes, filename: str) -> ResumeDocument | None:
        raw_text = file_bytes.decode("utf-8", errors="ignore")
        return ResumeDocument(
            filename=filename,
            raw_text=raw_text,
            extractor=self.name,
        )
