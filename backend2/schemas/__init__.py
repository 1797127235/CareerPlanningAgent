"""backend2/schemas — 跨模块公共数据契约。"""
from __future__ import annotations

from backend2.schemas.profile import (
    CareerSignals,
    Education,
    Internship,
    ParseCandidate,
    ProfileData,
    ResumeDocument,
    Skill,
)

__all__ = [
    "CareerSignals",
    "Education",
    "Internship",
    "ParseCandidate",
    "ProfileData",
    "ResumeDocument",
    "Skill",
]
