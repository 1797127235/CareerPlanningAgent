"""backend2/schemas — 跨模块公共数据契约。"""
from __future__ import annotations

from backend2.schemas.opportunity import (
    BasicRequirements,
    GapSkill,
    JDDiagnoseRequest,
    JDDiagnosisListItem,
    JDDiagnosisResponse,
    JDDiagnosisResult,
    JDExtract,
)
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

__all__ = [
    "BasicRequirements",
    "Education",
    "GapSkill",
    "Internship",
    "JDDiagnoseRequest",
    "JDDiagnosisListItem",
    "JDDiagnosisResponse",
    "JDDiagnosisResult",
    "JDExtract",
    "ParseMeta",
    "ParseResumePreviewResponse",
    "ProfileData",
    "Project",
    "ResumeDocument",
    "ResumeFile",
    "Skill",
]
