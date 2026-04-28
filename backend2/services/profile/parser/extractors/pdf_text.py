"""文字型 PDF 提取器 — 使用 pdfplumber。

遇到扫描件 PDF（无文字层）时返回 None，让注册表自动降到 OCR。
"""
from __future__ import annotations

import io
import logging

from backend2.schemas.profile import ResumeDocument
from backend2.services.profile.parser.base import TextExtractor

logger = logging.getLogger(__name__)
class PdfTextExtractor(TextExtractor):
    """从文字型 PDF 提取文本。扫描件 PDF 返回 None。

    注意：不在 extractor 层截断 raw_text。截断应在 strategy 内部生成 prompt 时进行，
    以便保留完整原文用于重新解析。
    """

    name = "pdfplumber"

    def supports(self, filename: str, content_type: str | None) -> bool:
        return filename.lower().endswith(".pdf") or content_type == "application/pdf"

    def extract(self, file_bytes: bytes, filename: str) -> ResumeDocument | None:
        try:
            import pdfplumber
        except ImportError:
            logger.warning("pdfplumber 未安装，跳过 PDF 文本提取")
            return None

        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                texts = [page.extract_text() or "" for page in pdf.pages]
                raw_text = "\n".join(texts)
        except Exception as e:
            logger.warning("PDF 文本提取失败: %s", e)
            return None

        if not raw_text.strip():
            logger.info("PDF 无可提取文字，疑似扫描件 — 自动降级到 OCR")
            return None  # 交给 OcrVlmExtractor

        return ResumeDocument(
            filename=filename,
            raw_text=raw_text,
            text_format="plain",
            extraction_method=self.name,
        )
