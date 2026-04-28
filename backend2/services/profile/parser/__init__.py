"""Resume parsing pipeline — unified entry point for backend2.

Usage:
    from backend2.services.profile.parser import ParserPipeline
    pipeline = ParserPipeline()
    result = pipeline.parse(resume_file)
"""
from __future__ import annotations

from backend2.services.profile.parser.base import TextExtractor
from backend2.services.profile.parser.pipeline import (
    ExtractorRegistry,
    ParserPipeline,
    default_registry,
)

__all__ = [
    "ExtractorRegistry",
    "ParserPipeline",
    "TextExtractor",
    "default_registry",
]
