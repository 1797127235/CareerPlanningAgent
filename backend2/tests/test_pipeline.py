"""Pipeline integration tests."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend2.schemas.profile import (
    ParseMeta,
    ParseResumePreviewResponse,
    ProfileData,
    ResumeDocument,
    ResumeFile,
)
from backend2.services.profile.parser.llm_parser import LLMParseResult
from backend2.services.profile.parser.pipeline import ExtractorRegistry, ParserPipeline


class TestExtractorRegistry:
    def test_extract_with_matching_extractor(self, sample_resume_file):
        registry = ExtractorRegistry()
        mock_extractor = MagicMock()
        mock_extractor.supports.return_value = True
        mock_extractor.extract.return_value = ResumeDocument(
            filename="test.txt",
            raw_text="extracted text",
            text_format="plain",
            extraction_method="mock",
        )
        registry.register(mock_extractor)

        doc = registry.extract(sample_resume_file)
        assert doc.raw_text == "extracted text"
        mock_extractor.supports.assert_called_once_with("test_resume.txt", "text/plain")

    def test_fallback_when_no_extractor_matches(self, sample_resume_file):
        registry = ExtractorRegistry()
        doc = registry.extract(sample_resume_file)
        assert doc.extraction_method == "raw_fallback"
        assert "Zhang San" in doc.raw_text

    def test_fallback_when_extractor_returns_none(self, sample_resume_file):
        registry = ExtractorRegistry()
        mock_extractor = MagicMock()
        mock_extractor.supports.return_value = True
        mock_extractor.extract.return_value = None
        registry.register(mock_extractor)

        doc = registry.extract(sample_resume_file)
        assert doc.extraction_method == "raw_fallback"


class TestParserPipeline:
    def test_successful_parse(self, sample_resume_file):
        pipeline = ParserPipeline()

        with patch("backend2.services.profile.parser.pipeline.llm_parse") as mock_llm:
            mock_llm.return_value = LLMParseResult(
                profile=ProfileData(name="Zhang San"),
                meta=ParseMeta(),
            )
            result = pipeline.parse(sample_resume_file)

        assert isinstance(result, ParseResumePreviewResponse)
        assert result.profile.name == "Zhang San"
        assert result.document.raw_text is not None
        assert result.meta.quality_score >= 0

    def test_parse_with_evidence(self, sample_resume_file):
        evidence_collector = MagicMock(return_value={"some": "evidence"})
        pipeline = ParserPipeline(evidence_collector=evidence_collector)

        with patch("backend2.services.profile.parser.pipeline.llm_parse") as mock_llm:
            mock_llm.return_value = LLMParseResult(
                profile=ProfileData(name="Zhang"),
                meta=ParseMeta(),
            )
            result = pipeline.parse(sample_resume_file)

        evidence_collector.assert_called_once_with(sample_resume_file)
        assert "resumesdk" in result.meta.evidence_sources

    def test_evidence_failure_continues(self, sample_resume_file):
        evidence_collector = MagicMock(side_effect=Exception("SDK down"))
        pipeline = ParserPipeline(evidence_collector=evidence_collector)

        with patch("backend2.services.profile.parser.pipeline.llm_parse") as mock_llm:
            mock_llm.return_value = LLMParseResult(
                profile=ProfileData(name="Zhang"),
                meta=ParseMeta(),
            )
            result = pipeline.parse(sample_resume_file)

        assert result.profile.name == "Zhang"
        assert any("SDK down" in w for w in result.meta.warnings)

    def test_llm_failure_returns_empty_profile(self, sample_resume_file):
        pipeline = ParserPipeline()

        with patch("backend2.services.profile.parser.pipeline.llm_parse") as mock_llm:
            mock_llm.return_value = None
            result = pipeline.parse(sample_resume_file)

        assert result.profile.name == ""
        assert any("LLM 解析失败" in w for w in result.meta.warnings)

    def test_pipeline_with_ocr_warning(self, sample_resume_file):
        registry = ExtractorRegistry()
        mock_extractor = MagicMock()
        mock_extractor.supports.return_value = True
        mock_extractor.extract.return_value = ResumeDocument(
            filename="test.pdf",
            raw_text="scanned text",
            text_format="plain",
            extraction_method="ocr",
            ocr_used=True,
            warnings=["OCR may have errors"],
        )
        registry.register(mock_extractor)

        pipeline = ParserPipeline(registry=registry)

        with patch("backend2.services.profile.parser.pipeline.llm_parse") as mock_llm:
            mock_llm.return_value = LLMParseResult(
                profile=ProfileData(name="Zhang"),
                meta=ParseMeta(),
            )
            result = pipeline.parse(sample_resume_file)

        assert any("OCR may have errors" in w for w in result.meta.warnings)
