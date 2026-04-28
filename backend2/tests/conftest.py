"""Shared test fixtures."""
from __future__ import annotations

import pytest

from backend2.schemas.profile import ResumeDocument, ResumeFile


@pytest.fixture
def sample_resume_file() -> ResumeFile:
    """A minimal ResumeFile fixture for testing."""
    return ResumeFile(
        filename="test_resume.txt",
        content_type="text/plain",
        file_bytes=b"Name: Zhang San\nSkills: Python, Java\n",
    )


@pytest.fixture
def sample_resume_document() -> ResumeDocument:
    """A minimal ResumeDocument fixture for testing."""
    return ResumeDocument(
        filename="test_resume.txt",
        content_type="text/plain",
        raw_text="Name: Zhang San\nSkills: Python, Java\n",
        text_format="plain",
        extraction_method="txt",
    )


@pytest.fixture
def sample_markdown_document() -> ResumeDocument:
    """A ResumeDocument with markdown text for date recovery testing."""
    return ResumeDocument(
        filename="test_resume.md",
        content_type="text/plain",
        raw_text=(
            "# Zhang San\n\n"
            "## Education\n"
            "Tsinghua University, CS, 2020.09 - 2024.06\n\n"
            "## Internship\n"
            "ByteDance, Backend, 2024.03 - 2024.08\n"
        ),
        text_format="plain",
        extraction_method="txt",
    )
