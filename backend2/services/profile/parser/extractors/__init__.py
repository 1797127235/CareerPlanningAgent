"""文本提取器 — 将文件转为 ResumeDocument。"""
from __future__ import annotations

from backend2.services.profile.parser.extractors.docx_text import DocxTextExtractor
from backend2.services.profile.parser.extractors.markitdown_extractor import MarkItDownExtractor
from backend2.services.profile.parser.extractors.ocr_vlm import OcrVlmExtractor
from backend2.services.profile.parser.extractors.pdf_text import PdfTextExtractor
from backend2.services.profile.parser.extractors.txt_text import TxtTextExtractor

__all__ = [
    "DocxTextExtractor",
    "MarkItDownExtractor",
    "OcrVlmExtractor",
    "PdfTextExtractor",
    "TxtTextExtractor",
]
