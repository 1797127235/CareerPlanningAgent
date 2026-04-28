"""Extractor tests."""
from __future__ import annotations

from backend2.schemas.profile import ResumeDocument
from backend2.services.profile.parser.extractors.docx_text import DocxTextExtractor
from backend2.services.profile.parser.extractors.ocr_vlm import OcrVlmExtractor
from backend2.services.profile.parser.extractors.markitdown_extractor import MarkItDownExtractor
from backend2.services.profile.parser.extractors.pdf_text import PdfTextExtractor
from backend2.services.profile.parser.extractors.txt_text import TxtTextExtractor


class TestTxtTextExtractor:
    def test_supports_txt(self):
        ex = TxtTextExtractor()
        assert ex.supports("resume.txt", None) is True
        assert ex.supports("resume.md", None) is True
        assert ex.supports("resume.pdf", None) is False

    def test_supports_content_type(self):
        ex = TxtTextExtractor()
        assert ex.supports("resume", "text/plain") is True

    def test_extract_utf8(self):
        ex = TxtTextExtractor()
        doc = ex.extract("Hello World".encode("utf-8"), "test.txt")
        assert doc is not None
        assert doc.raw_text == "Hello World"
        assert doc.extraction_method == "txt"
        assert doc.text_format == "plain"

    def test_extract_with_invalid_bytes(self):
        ex = TxtTextExtractor()
        doc = ex.extract(b"\xff\xfeHello", "test.txt")
        assert doc is not None
        assert "Hello" in doc.raw_text


class TestPdfTextExtractor:
    def test_supports_pdf(self):
        ex = PdfTextExtractor()
        assert ex.supports("resume.pdf", None) is True
        assert ex.supports("resume.pdf", "application/pdf") is True
        assert ex.supports("resume.txt", None) is False

    def test_extract_empty_returns_none(self):
        ex = PdfTextExtractor()
        doc = ex.extract(b"not a pdf", "test.pdf")
        assert doc is None

    def test_extract_non_pdf_bytes(self):
        ex = PdfTextExtractor()
        doc = ex.extract(b"plain text", "test.txt")
        assert doc is None


class TestDocxTextExtractor:
    def test_supports_docx(self):
        ex = DocxTextExtractor()
        assert ex.supports("resume.docx", None) is True
        assert ex.supports("resume.txt", None) is False

    def test_extract_without_python_docx(self):
        ex = DocxTextExtractor()
        result = ex.extract(b"not a docx", "test.docx")
        assert result is None or isinstance(result, ResumeDocument)


class TestOcrVlmExtractor:
    def test_supports_pdf(self):
        ex = OcrVlmExtractor()
        assert ex.supports("resume.pdf", None) is True
        assert ex.supports("resume.txt", None) is False

    def test_extract_without_api_key(self):
        ex = OcrVlmExtractor()
        doc = ex.extract(b"any", "test.pdf")
        assert doc is None


class TestMarkItDownExtractor:
    def test_supports_pdf(self):
        ex = MarkItDownExtractor()
        assert ex.supports("resume.pdf", None) is True
        assert ex.supports("resume.docx", None) is True
        assert ex.supports("resume.txt", None) is False

    def test_supports_docx_content_type(self):
        ex = MarkItDownExtractor()
        assert ex.supports("resume", "application/pdf") is True
        assert ex.supports(
            "resume",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ) is True

    def test_extract_text_bytes_as_markdown(self):
        ex = MarkItDownExtractor()
        doc = ex.extract(b"not a valid document", "test.pdf")
        # markitdown is lenient and may convert plain text bytes
        if doc is not None:
            assert doc.text_format == "markdown"
            assert doc.extraction_method == "markitdown"

    def test_text_format_is_markdown(self):
        ex = MarkItDownExtractor()
        doc = ex.extract(b"not a valid document", "test.docx")
        if doc is not None:
            assert doc.text_format == "markdown"
            assert doc.extraction_method == "markitdown"
