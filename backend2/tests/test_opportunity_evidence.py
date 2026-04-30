"""Tests for backend2/services/opportunity/evidence.py — 纯本地技能匹配。"""
from __future__ import annotations

import pytest

from backend2.schemas.opportunity import BasicRequirements, JDExtract
from backend2.schemas.profile import Internship, ProfileData, Project, Skill
from backend2.services.opportunity.evidence import (
    _collect_user_skills,
    _match_skill,
    build_skill_evidence,
)


class TestCollectUserSkills:
    """_collect_user_skills: 从 ProfileData 提取所有技能名称。"""

    def test_skills_from_profile_skills(self):
        profile = ProfileData(skills=[
            Skill(name="Python", level="advanced"),
            Skill(name="React", level="familiar"),
        ])
        skills = _collect_user_skills(profile)
        assert skills == {"python", "react"}

    def test_skills_from_project_tech_stack(self):
        profile = ProfileData(projects=[
            Project(name="MyApp", tech_stack=["Django", "PostgreSQL"]),
            Project(name="API", tech_stack=["FastAPI"]),
        ])
        skills = _collect_user_skills(profile)
        assert "django" in skills
        assert "postgresql" in skills
        assert "fastapi" in skills

    def test_skills_from_internship_tech_stack(self):
        profile = ProfileData(internships=[
            Internship(company="ByteDance", role="Backend", tech_stack=["Go", "Redis"]),
        ])
        skills = _collect_user_skills(profile)
        assert "go" in skills
        assert "redis" in skills

    def test_deduplicates_case_insensitive(self):
        profile = ProfileData(skills=[
            Skill(name="Python"),
            Skill(name="python"),
            Skill(name="PYTHON"),
        ])
        skills = _collect_user_skills(profile)
        assert skills == {"python"}

    def test_empty_profile(self):
        profile = ProfileData()
        skills = _collect_user_skills(profile)
        assert skills == set()

    def test_combined_sources(self):
        profile = ProfileData(
            skills=[Skill(name="Python")],
            projects=[Project(tech_stack=["Django"])],
            internships=[Internship(tech_stack=["Redis"])],
        )
        skills = _collect_user_skills(profile)
        assert skills == {"python", "django", "redis"}


class TestMatchSkill:
    """_match_skill: 精确匹配（大小写不敏感），不做子串匹配。"""

    def test_exact_match(self):
        assert _match_skill("Python", {"python", "java"}) is True

    def test_case_insensitive(self):
        """_match_skill 做 lowercase 匹配，user_skills 集合必须已是 lowercase。"""
        assert _match_skill("python", {"python"}) is True
        assert _match_skill("PYTHON", {"python"}) is True

    def test_no_substring_match(self):
        """Go 不应命中 MongoDB"""
        assert _match_skill("Go", {"mongodb"}) is False
        assert _match_skill("C", {"react"}) is False

    def test_empty_skill(self):
        assert _match_skill("", {"python"}) is False
        assert _match_skill("  ", {"python"}) is False

    def test_not_found(self):
        assert _match_skill("Kubernetes", {"python", "java"}) is False


class TestBuildSkillEvidence:
    """build_skill_evidence: 构建匹配证据字典。"""

    def test_basic_evidence(self):
        profile = ProfileData(skills=[Skill(name="Python"), Skill(name="Go")])
        jd = JDExtract(
            required_skills=["Python", "Kubernetes"],
            preferred_skills=["Go", "Redis"],
        )
        evidence = build_skill_evidence(profile, jd)

        assert evidence["matched_required"] == ["Python"]
        assert evidence["gap_required"] == ["Kubernetes"]
        assert evidence["matched_preferred"] == ["Go"]
        assert evidence["gap_preferred"] == ["Redis"]

    def test_coverage_formatting(self):
        profile = ProfileData(skills=[Skill(name="Python")])
        jd = JDExtract(required_skills=["Python", "Java", "Go"])
        evidence = build_skill_evidence(profile, jd)

        assert evidence["required_coverage"] == "1/3 (33%)"

    def test_empty_jd(self):
        profile = ProfileData(skills=[Skill(name="Python")])
        jd = JDExtract()
        evidence = build_skill_evidence(profile, jd)

        assert evidence["required_skills"] == []
        assert evidence["preferred_skills"] == []
        assert evidence["matched_required"] == []
        assert evidence["gap_required"] == []

    def test_no_user_skills(self):
        profile = ProfileData()
        jd = JDExtract(required_skills=["Python"])
        evidence = build_skill_evidence(profile, jd)

        assert evidence["matched_required"] == []
        assert evidence["gap_required"] == ["Python"]

    def test_user_skills_sorted(self):
        profile = ProfileData(skills=[
            Skill(name="Zebra"),
            Skill(name="Alpha"),
            Skill(name="Middle"),
        ])
        jd = JDExtract(required_skills=["Alpha"])
        evidence = build_skill_evidence(profile, jd)

        assert evidence["user_skills"] == ["alpha", "middle", "zebra"]
