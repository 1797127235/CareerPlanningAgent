"""Profile schema definitions — single source of truth for resume-parsed profile structure."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Skill(BaseModel):
    name: str = Field(..., min_length=1)
    level: Literal["beginner", "familiar", "intermediate", "advanced"] = "familiar"


class Education(BaseModel):
    degree: str = ""
    major: str = ""
    school: str = ""
    graduation_year: int | None = None


class Internship(BaseModel):
    company: str = ""
    role: str = ""
    duration: str = ""
    tech_stack: list[str] = Field(default_factory=list)
    highlights: str = ""


class CareerSignals(BaseModel):
    has_publication: bool = False
    publication_level: str = "无"
    competition_awards: list[str] = Field(default_factory=list)
    domain_specialization: str = ""
    research_vs_engineering: Literal["research", "engineering", "balanced"] = "balanced"
    open_source: bool = False
    internship_company_tier: str = "无"


class ProfileData(BaseModel):
    """Standard profile schema — the canonical output of the parsing pipeline."""

    name: str = ""
    job_target: str = ""
    primary_domain: str = ""
    career_signals: CareerSignals = Field(default_factory=CareerSignals)
    experience_years: int = 0
    education: Education = Field(default_factory=Education)
    skills: list[Skill] = Field(default_factory=list)
    knowledge_areas: list[str] = Field(default_factory=list)
    internships: list[Internship] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    awards: list[str] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)
    raw_text: str = ""
    soft_skills: dict = Field(default_factory=lambda: {
        "_version": 2,
        "communication": None,
        "learning": None,
        "collaboration": None,
        "innovation": None,
        "resilience": None,
    })
    preferences: dict | None = None
    _source: str = ""  # "resumesdk", "llm", "manual"

    @field_validator("skills", mode="before")
    @classmethod
    def normalize_skills(cls, v: list) -> list:
        """Ensure skills are dicts with name+level, filtering empties."""
        if not isinstance(v, list):
            return []
        out = []
        for item in v:
            if isinstance(item, dict) and item.get("name"):
                out.append(item)
            elif isinstance(item, str) and item.strip():
                out.append({"name": item.strip(), "level": "familiar"})
        return out

    @field_validator("projects", "awards", "certificates", "knowledge_areas", mode="before")
    @classmethod
    def dedupe_strings(cls, v: list) -> list:
        """Deduplicate string lists preserving order."""
        if not isinstance(v, list):
            return []
        seen = set()
        out = []
        for item in v:
            if isinstance(item, str):
                key = item.strip()
                if key and key not in seen:
                    seen.add(key)
                    out.append(key)
        return out

    def to_dict(self) -> dict:
        """Serialize to plain dict for JSON storage / API response."""
        return self.model_dump(mode="json")

