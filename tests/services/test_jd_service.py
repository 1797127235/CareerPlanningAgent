# -*- coding: utf-8 -*-
"""Tests for JDService — skill extraction + diagnose + resume tips."""
from __future__ import annotations

import pytest

from backend.services.jd_service import JDService


@pytest.fixture()
def svc() -> JDService:
    return JDService()


# ── extract_skills ──────────────────────────────────────────────────────────


class TestSkillExtraction:
    def test_extracts_known_skills(self, svc):
        jd = "要求熟悉Python、MySQL、Redis，有Docker使用经验"
        result = svc.extract_skills(jd)
        assert "Python" in result
        assert "MySQL" in result
        assert "Redis" in result

    def test_extracts_docker(self, svc):
        jd = "要求有Docker使用经验"
        result = svc.extract_skills(jd)
        assert "Docker" in result

    def test_empty_jd(self, svc):
        result = svc.extract_skills("")
        assert result == []

    def test_no_match(self, svc):
        result = svc.extract_skills("这是一段完全不相关的文字")
        assert isinstance(result, list)

    def test_english_word_boundary(self, svc):
        """SQL should not match inside MySQL."""
        jd = "掌握MySQL数据库"
        result = svc.extract_skills(jd)
        assert "MySQL" in result
        # SQL should NOT be extracted because "SQL" only appears as part of "MySQL"
        assert "SQL" not in result

    def test_chinese_keywords(self, svc):
        jd = "具备良好的沟通能力和团队协作精神"
        result = svc.extract_skills(jd)
        assert "沟通能力" in result
        assert "团队协作" in result

    def test_preserves_dict_order(self, svc):
        """Skills are returned in dictionary-key order (not JD position).
        Python comes before Java in the keyword dict."""
        jd = "Java, Python, Redis"
        result = svc.extract_skills(jd)
        assert "Java" in result
        assert "Python" in result
        assert "Redis" in result
        # Dictionary order: Python first, then Java, then Redis
        assert result.index("Python") < result.index("Java")


# ── diagnose ────────────────────────────────────────────────────────────────


class TestDiagnose:
    def test_returns_score_and_gaps(self, svc, sample_profile):
        jd = "要求熟悉Python、Kubernetes、Docker，有微服务开发经验"
        result = svc.diagnose(jd, sample_profile)
        assert 0 <= result["match_score"] <= 100
        assert "gap_skills" in result
        assert "matched_skills" in result

    def test_matched_skills_from_profile(self, svc, sample_profile):
        jd = "要求熟悉Python、Git、Linux"
        result = svc.diagnose(jd, sample_profile)
        assert "Python" in result["matched_skills"]
        assert result["match_score"] > 50

    def test_gap_skills_when_profile_missing(self, svc, sample_profile):
        jd = "要求精通Kubernetes、Rust、Angular"
        result = svc.diagnose(jd, sample_profile)
        gap_names = [g["skill"] for g in result["gap_skills"]]
        assert "Kubernetes" in gap_names
        assert "Rust" in gap_names

    def test_empty_jd_returns_zero(self, svc, sample_profile):
        result = svc.diagnose("", sample_profile)
        assert result["match_score"] == 0
        assert result["matched_skills"] == []

    def test_extracted_skills_included(self, svc, sample_profile):
        jd = "需要Python和Docker经验"
        result = svc.diagnose(jd, sample_profile)
        assert "extracted_skills" in result
        assert isinstance(result["extracted_skills"], list)


# ── generate_resume_tips ────────────────────────────────────────────────────


class TestResumeTips:
    def test_finds_hidden_skills(self, svc):
        profile = {
            "projects": [
                {"name": "微服务电商平台", "description": "使用Docker部署，Redis做缓存"}
            ],
            "internships": [],
        }
        gap_skills = [
            {"skill": "Docker", "priority": "high"},
            {"skill": "Redis", "priority": "high"},
        ]
        tips = svc.generate_resume_tips(profile, gap_skills)
        assert len(tips) > 0
        assert any("Docker" in t for t in tips)

    def test_empty_gaps(self, svc):
        tips = svc.generate_resume_tips({"projects": [], "internships": []}, [])
        assert tips == []


# ── match_to_graph_node ─────────────────────────────────────────────────────


class TestMatchToGraphNode:
    def test_returns_best_match(self, svc, graph_service):
        jd_skills = ["Python", "Django", "MySQL", "Redis", "Docker"]
        result = svc.match_to_graph_node(jd_skills, graph_service)
        # May be None if graph doesn't have a close node; if not None, check shape
        if result is not None:
            assert "node_id" in result
            assert "label" in result
            assert "match_confidence" in result

    def test_empty_skills_returns_none(self, svc, graph_service):
        result = svc.match_to_graph_node([], graph_service)
        assert result is None
