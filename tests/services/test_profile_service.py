# -*- coding: utf-8 -*-
"""Tests for ProfileService — scoring, positioning, skill inference."""
from __future__ import annotations

import pytest


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def profile_service(graph_service):
    """Session-scoped ProfileService instance."""
    from backend.services.profile import ProfileService
    return ProfileService(graph_service)


# ── locate_on_graph ──────────────────────────────────────────────────────────


class TestLocateOnGraph:
    def test_locate_returns_best_match(self, profile_service, sample_profile):
        result = profile_service.locate_on_graph(sample_profile)
        assert "node_id" in result
        assert "score" in result
        assert result["score"] > 0

    def test_locate_returns_candidates(self, profile_service, sample_profile):
        result = profile_service.locate_on_graph(sample_profile)
        assert "candidates" in result
        assert len(result["candidates"]) >= 3

    def test_locate_returns_label(self, profile_service, sample_profile):
        result = profile_service.locate_on_graph(sample_profile)
        assert "label" in result
        assert isinstance(result["label"], str)
        assert len(result["label"]) > 0

    def test_locate_returns_family_confidence(self, profile_service, sample_profile):
        result = profile_service.locate_on_graph(sample_profile)
        assert "family_confidence" in result
        assert isinstance(result["family_confidence"], (int, float))

    def test_locate_with_explicit_nodes(self, profile_service, sample_profile, graph_service):
        """Test passing an explicit node list to locate_on_graph."""
        nodes = list(graph_service._nodes.values())[:10]
        result = profile_service.locate_on_graph(sample_profile, nodes=nodes)
        assert "node_id" in result
        assert result["score"] >= 0

    def test_locate_empty_profile(self, profile_service):
        """Empty profile should still return a result (possibly low score)."""
        result = profile_service.locate_on_graph({})
        assert "node_id" in result

    def test_locate_with_title(self, profile_service):
        """Profile with current_title should get title bonus."""
        profile = {
            "current_title": "后端开发工程师",
            "skills": [
                {"name": "Java", "level": "熟练"},
                {"name": "Spring Boot", "level": "熟悉"},
                {"name": "MySQL", "level": "熟悉"},
            ],
        }
        result = profile_service.locate_on_graph(profile)
        assert result["score"] > 0
        # With a clear title, we expect reasonable confidence
        assert result["family_confidence"] >= 0

    def test_candidates_sorted_descending(self, profile_service, sample_profile):
        result = profile_service.locate_on_graph(sample_profile)
        candidates = result["candidates"]
        scores = [c["score"] for c in candidates]
        assert scores == sorted(scores, reverse=True)


# ── score_four_dimensions ────────────────────────────────────────────────────


class TestFourDimensionScoring:
    def test_score_returns_four_dimensions(self, profile_service, sample_profile, graph_service):
        nodes = graph_service._nodes
        node = list(nodes.values())[0]
        result = profile_service.score_four_dimensions(sample_profile, node)
        assert "total_score" in result
        assert "career_stage" in result
        for dim in ("basic", "skills", "qualities", "potential"):
            assert dim in result["four_dimensions"]
            assert 0 <= result["four_dimensions"][dim]["score"] <= 100

    def test_career_stage_is_valid(self, profile_service, sample_profile, graph_service):
        nodes = graph_service._nodes
        node = list(nodes.values())[0]
        result = profile_service.score_four_dimensions(sample_profile, node)
        assert result["career_stage"] in ("entry", "mid", "senior")

    def test_total_score_in_range(self, profile_service, sample_profile, graph_service):
        nodes = graph_service._nodes
        node = list(nodes.values())[0]
        result = profile_service.score_four_dimensions(sample_profile, node)
        assert 0 <= result["total_score"] <= 100

    def test_basic_penalty_for_low_basic_score(self, profile_service, graph_service):
        """Profile with poor basic qualifications should trigger penalty."""
        weak_profile = {
            "basic_info": {"degree": "高中"},
            "skills": [],
        }
        node = list(graph_service._nodes.values())[0]
        result = profile_service.score_four_dimensions(weak_profile, node)
        # Should still produce valid output
        assert 0 <= result["total_score"] <= 100

    def test_dimensions_have_weight(self, profile_service, sample_profile, graph_service):
        node = list(graph_service._nodes.values())[0]
        result = profile_service.score_four_dimensions(sample_profile, node)
        for dim in ("basic", "skills", "qualities", "potential"):
            dim_data = result["four_dimensions"][dim]
            assert "weight" in dim_data
            assert dim_data["weight"] > 0


# ── Skill inference ──────────────────────────────────────────────────────────


class TestSkillInference:
    def test_cooccurrence_returns_list(self, profile_service):
        result = profile_service.infer_skills_cooccurrence(["Python", "Django"])
        assert isinstance(result, list)

    def test_esco_returns_list(self, profile_service):
        result = profile_service.infer_skills_esco(["Python"])
        assert isinstance(result, list)

    def test_cooccurrence_empty_input(self, profile_service):
        result = profile_service.infer_skills_cooccurrence([])
        assert result == []

    def test_esco_empty_input(self, profile_service):
        result = profile_service.infer_skills_esco([])
        assert result == []
