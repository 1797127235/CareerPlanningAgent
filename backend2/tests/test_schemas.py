"""Schema validation tests."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend2.schemas.profile import (
    Education,
    Internship,
    ParseMeta,
    ParseResumePreviewResponse,
    ProfileData,
    Project,
    ResumeDocument,
    ResumeFile,
    Skill,
)


class TestResumeFile:
    def test_basic_creation(self):
        rf = ResumeFile(filename="test.pdf", content_type="application/pdf", file_bytes=b"pdfdata")
        assert rf.filename == "test.pdf"
        assert rf.content_type == "application/pdf"
        assert rf.file_bytes == b"pdfdata"

    def test_file_bytes_excluded_from_serialization(self):
        rf = ResumeFile(filename="test.txt", file_bytes=b"data")
        dumped = rf.model_dump()
        assert "file_bytes" not in dumped


class TestResumeDocument:
    def test_defaults(self):
        doc = ResumeDocument(filename="test.txt", raw_text="hello")
        assert doc.text_format == "plain"
        assert doc.extraction_method == ""
        assert doc.ocr_used is False
        assert doc.warnings == []

    def test_markdown_format(self):
        doc = ResumeDocument(
            filename="test.md",
            raw_text="# Title",
            text_format="markdown",
            extraction_method="markitdown",
        )
        assert doc.text_format == "markdown"


class TestProfileData:
    def test_defaults(self):
        pd = ProfileData()
        assert pd.name == ""
        assert pd.education == []
        assert pd.skills == []
        assert pd.projects == []
        assert pd.internships == []

    def test_skill_normalization(self):
        pd = ProfileData(skills=["Python", {"name": "Java", "level": "advanced"}, "", "  "])
        assert len(pd.skills) == 2
        assert pd.skills[0].name == "Python"
        assert pd.skills[0].level == "familiar"
        assert pd.skills[1].name == "Java"
        assert pd.skills[1].level == "advanced"

    def test_string_list_dedupe(self):
        pd = ProfileData(awards=["Award A", "  award a  ", "Award B", ""])
        assert pd.awards == ["Award A", "Award B"]

    def test_education_as_list(self):
        pd = ProfileData(education=[
            {"degree": "Bachelor", "major": "CS", "school": "THU"},
            {"degree": "Master", "major": "AI", "school": "PKU"},
        ])
        assert len(pd.education) == 2
        assert pd.education[0].school == "THU"
        assert pd.education[1].school == "PKU"

    def test_model_dump(self):
        pd = ProfileData(name="Test", skills=[{"name": "Python"}])
        d = pd.to_dict()
        assert d["name"] == "Test"
        assert d["skills"] == [{"name": "Python", "level": "familiar"}]


class TestSkill:
    def test_level_default(self):
        s = Skill(name="Python")
        assert s.level == "familiar"

    def test_invalid_level(self):
        with pytest.raises(ValidationError):
            Skill(name="Python", level="expert")


class TestParseResumePreviewResponse:
    def test_basic_response(self):
        profile = ProfileData(name="Test")
        document = ResumeDocument(filename="test.txt", raw_text="hello")
        meta = ParseMeta(quality_score=75)
        resp = ParseResumePreviewResponse(profile=profile, document=document, meta=meta)
        assert resp.profile.name == "Test"
        assert resp.meta.quality_score == 75
