# -*- coding: utf-8 -*-
"""ProfileService facade — delegates to sub-modules by domain."""
from __future__ import annotations

import json
from typing import Any

from backend.services.profile.shared import _PROFILES_PATH
from backend.services.profile import locator, scorer, sjt, cooccurrence


class ProfileService:
    """Unified profile analysis service.

    Replaces 5 separate algorithm files with one Service class:
    - locate_on_graph.py → locate_on_graph()
    - profile_scorer.py → score_four_dimensions()
    - sjt_scorer.py → score_sjt_v2()
    - skill_cooccurrence.py → infer_skills_cooccurrence()

    # TODO: infer_skills_esco 规划中未实现
    """

    def __init__(self, graph_service: Any):
        from backend.services.graph_service import GraphService
        self._graph: GraphService = graph_service
        self._profiles_cache: dict[str, Any] | None = None
        self._cross_direction_idf: dict[str, float] | None = None
        self._cooccurrence_state = cooccurrence.CoocState()

    # ── Public API：薄包装 delegate ──────────────────────────

    def compute_quality(self, profile_data: dict) -> dict:
        return scorer.compute_quality(profile_data)

    def locate_on_graph(self, profile: dict, nodes: list[dict] | None = None) -> dict:
        return locator.locate_on_graph(profile, self._graph, nodes)

    def score_four_dimensions(
        self,
        profile: dict,
        target_node: dict,
        db_session: Any = None,
        sjt_scores: dict[str, float] | None = None,
    ) -> dict:
        return scorer.score_four_dimensions(
            profile,
            target_node,
            self._get_cross_direction_idf(),
            self._load_profiles(),
            db_session,
            sjt_scores,
        )

    def generate_sjt_questions(self, profile_data: dict) -> list[dict]:
        return sjt.generate_sjt_questions(profile_data)

    def score_sjt_v2(self, answers: list[dict], questions: list[dict]) -> dict:
        return sjt.score_sjt_v2(answers, questions)

    def generate_sjt_advice(
        self,
        dimensions: dict,
        answers: list[dict],
        questions: list[dict],
        profile_data: dict,
    ) -> dict[str, str]:
        return sjt.generate_sjt_advice(dimensions, answers, questions, profile_data)

    def infer_skills_cooccurrence(
        self,
        skills: list[str],
        min_cooccurrence: float = 0.6,
        min_similarity: float = 0.85,
        max_inferred: int = 10,
    ) -> list[str]:
        return cooccurrence.infer_skills_cooccurrence(
            skills,
            self._cooccurrence_state,
            min_cooccurrence=min_cooccurrence,
            min_similarity=min_similarity,
            max_inferred=max_inferred,
        )

    def infer_skills_esco(self, skills: list[str]) -> list[str]:
        """TODO: ESCO DAG-based skill inference — not yet implemented."""
        return []

    # ── 共享 cache（跨子模块使用） ────────────────────────────

    def _load_profiles(self) -> dict[str, Any]:
        """Lazy-load profiles.json."""
        if self._profiles_cache is None:
            if _PROFILES_PATH.exists():
                self._profiles_cache = json.loads(
                    _PROFILES_PATH.read_text(encoding="utf-8")
                )
            else:
                self._profiles_cache = {}
        return self._profiles_cache

    def _get_cross_direction_idf(self) -> dict[str, float]:
        """Lazy-compute cross-direction IDF."""
        if self._cross_direction_idf is None:
            self._cross_direction_idf = scorer.compute_idf_cross_direction(
                self._load_profiles()
            )
        return self._cross_direction_idf
