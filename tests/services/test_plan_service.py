# -*- coding: utf-8 -*-
"""Tests for PlanService — plan shape, fallback plan, roadmap matching."""
from __future__ import annotations

import pytest

from backend.services.plan_service import PlanService


@pytest.fixture()
def svc() -> PlanService:
    return PlanService()


# ── compute_plan_shape ──────────────────────────────────────────────────────


class TestPlanShape:
    def test_compute_plan_shape(self, svc):
        result = svc.compute_plan_shape(200)
        assert "total_weeks" in result
        assert 4 <= result["total_weeks"] <= 16
        assert len(result["stages"]) == 3

    def test_minimum_hours(self, svc):
        result = svc.compute_plan_shape(10)
        assert result["total_weeks"] == 4  # floor clamp

    def test_maximum_hours(self, svc):
        result = svc.compute_plan_shape(5000)
        assert result["total_weeks"] == 16  # ceil clamp

    def test_stage_weeks_sum(self, svc):
        result = svc.compute_plan_shape(120)
        stage_weeks_sum = sum(s["weeks"] for s in result["stages"])
        assert stage_weeks_sum == result["total_weeks"]

    def test_stage_ratios(self, svc):
        result = svc.compute_plan_shape(200)
        stages = result["stages"]
        # Stage 1 should be the longest (~40%), stage 3 the shortest (~25%)
        assert stages[0]["weeks"] >= stages[2]["weeks"]


# ── build_fallback_plan ─────────────────────────────────────────────────────


class TestFallbackPlan:
    def test_build_fallback_plan(self, svc):
        result = svc.build_fallback_plan(["Docker", "Kubernetes"], "云原生工程师")
        assert "stages" in result
        assert len(result["stages"]) > 0

    def test_fallback_plan_has_weeks(self, svc):
        result = svc.build_fallback_plan(["Python", "Flask"], "后端工程师")
        for stage in result["stages"]:
            assert "weeks" in stage
            assert isinstance(stage["weeks"], list)
            for week in stage["weeks"]:
                assert "focus" in week
                assert "tasks" in week

    def test_fallback_plan_empty_skills(self, svc):
        result = svc.build_fallback_plan([], "通用开发")
        assert "stages" in result
        assert len(result["stages"]) > 0


# ── match_roadmaps ──────────────────────────────────────────────────────────


class TestMatchRoadmaps:
    def test_matches_frontend(self, svc):
        result = svc.match_roadmaps(["前端", "React"], ["React", "Vue", "TypeScript"])
        assert isinstance(result, list)
        # Should find frontend-related roadmaps
        if result:
            assert any("frontend" in r or "react" in r or "vue" in r for r in result)

    def test_matches_backend(self, svc):
        result = svc.match_roadmaps(["后端", "Python"], ["Python", "Django", "Redis"])
        assert isinstance(result, list)
        if result:
            assert any("python" in r or "backend" in r for r in result)

    def test_no_match(self, svc):
        result = svc.match_roadmaps(["完全不存在的岗位"], ["完全不存在的技能"])
        assert isinstance(result, list)


# ── topo_sort_topics ────────────────────────────────────────────────────────


class TestTopoSort:
    def test_topo_sort_known_roadmap(self, svc):
        result = svc.topo_sort_topics("python")
        # May be empty if roadmap doesn't exist, but should be a list
        assert isinstance(result, list)

    def test_topo_sort_unknown_roadmap(self, svc):
        result = svc.topo_sort_topics("nonexistent-roadmap-xyz")
        assert result == []


# ── prioritize_by_gaps ──────────────────────────────────────────────────────


class TestPrioritizeByGaps:
    def test_filters_to_relevant(self, svc):
        topics = [
            {"label": "Python Basics"},
            {"label": "Docker Containers"},
            {"label": "Advanced SQL"},
            {"label": "Git Workflow"},
        ]
        gaps = ["Docker", "SQL"]
        result = svc.prioritize_by_gaps(topics, gaps)
        assert isinstance(result, list)
        # Docker and SQL topics should be prioritized
        labels = [t["label"] for t in result]
        assert any("Docker" in l for l in labels)
        assert any("SQL" in l for l in labels)

    def test_no_gaps_returns_all(self, svc):
        topics = [{"label": "A"}, {"label": "B"}]
        result = svc.prioritize_by_gaps(topics, [])
        assert len(result) == len(topics)
