"""MarkItDown 提取器 — 将 PDF/DOCX 转为 Markdown。

注册顺序应在 PdfTextExtractor / DocxTextExtractor 之前，
优先尝试保留 Markdown 格式；失败时返回 None 让注册表降级。
"""
from __future__ import annotations

import io
import logging

from backend2.schemas.profile import ResumeDocument
from backend2.services.profile.parser.base import TextExtractor

logger = logging.getLogger(__name__)


class MarkItDownExtractor(TextExtractor):
    """使用 markitdown 将 PDF/DOCX 转为 Markdown。

    优势：Markdown 比纯文本更能保留标题、列表、日期附近的上下文。
    """

    name = "markitdown"

    def supports(self, filename: str, content_type: str | None) -> bool:
        fn = filename.lower()
        return (
            fn.endswith(".pdf")
            or fn.endswith(".docx")
            or fn.endswith(".doc")
            or content_type == "application/pdf"
            or content_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    def extract(self, file_bytes: bytes, filename: str) -> ResumeDocument | None:
        try:
            from markitdown import MarkItDown
        except ImportError:
            logger.warning("markitdown 未安装，跳过 Markdown 提取")
            return None

        try:
            md = MarkItDown()
            result = md.convert(io.BytesIO(file_bytes))
            raw_text = result.text_content if result else ""
            if not raw_text.strip():
                logger.warning("markitdown 返回空文本: %s", filename)
                return None

            return ResumeDocument(
                filename=filename,
                raw_text=raw_text,
                text_format="markdown",
                extraction_method=self.name,
            )
        except Exception as e:
            logger.warning("markitdown 提取失败: %s", e)
            return None
