"""Resume parsing pipeline — unified entry point for backend2.

Usage:
    from backend2.services.profile.parser import ResumeParserPipeline
    pipeline = ResumeParserPipeline()
    result = pipeline.parse(file_bytes, filename)
"""
from __future__ import annotations

from backend2.services.profile.parser.base import ParseStrategy, TextExtractor
from backend2.services.profile.parser.pipeline import (
    ExtractorRegistry,
    ParseResult,
    ResumeParserPipeline,
    default_pipeline,
)

__all__ = [
    "ExtractorRegistry",
    "ParseResult",
    "ParseStrategy",
    "ResumeParserPipeline",
    "TextExtractor",
    "default_pipeline",
]
