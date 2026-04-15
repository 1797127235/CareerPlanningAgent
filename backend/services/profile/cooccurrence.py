# -*- coding: utf-8 -*-
"""Skill co-occurrence inference based on evidence data."""
from __future__ import annotations

import json
from collections import defaultdict
from itertools import combinations
from typing import Any

from backend.services.profile.shared import (
    _EVIDENCE_PATH,
    _SKILL_EMBEDDINGS_PATH,
    _cosine_similarity,
)


class CoocState:
    """Mutable state container for co-occurrence cache (owned by service facade)."""

    def __init__(self) -> None:
        self.loaded = False
        self.conditional: dict[str, list[tuple[str, float]]] = {}
        self.skill_count: dict[str, int] = {}
        self.total_jds: int = 0
        self.skill_embeddings: dict[str, list[float]] | None = None


def _ensure_cooccurrence_loaded(state: CoocState) -> None:
    """Lazy-load co-occurrence graph from evidence.jsonl into state."""
    if state.loaded:
        return
    state.loaded = True

    if not _EVIDENCE_PATH.exists():
        return

    pair_count: dict[tuple[str, str], int] = defaultdict(int)
    skill_count: dict[str, int] = defaultdict(int)
    total_jds = 0

    with open(_EVIDENCE_PATH, encoding="utf-8") as f:
        for line in f:
            try:
                jd = json.loads(line)
            except json.JSONDecodeError:
                continue

            skills_raw = jd.get("skills", [])
            if not isinstance(skills_raw, list):
                continue

            skill_names: set[str] = set()
            for s in skills_raw:
                if not isinstance(s, dict):
                    continue
                cat = (s.get("category") or "").lower()
                if cat == "soft_skill":
                    continue
                name = (s.get("name") or "").strip()
                if name:
                    skill_names.add(name)

            if len(skill_names) < 2:
                continue

            total_jds += 1
            for name in skill_names:
                skill_count[name] += 1

            for a, b in combinations(sorted(skill_names), 2):
                pair_count[(a, b)] += 1

    state.skill_count = dict(skill_count)
    state.total_jds = total_jds

    # Build conditional probability index: P(B|A) = count(A,B) / count(A)
    conditional: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for (a, b), count in pair_count.items():
        prob_b_given_a = count / skill_count[a] if skill_count[a] > 0 else 0
        prob_a_given_b = count / skill_count[b] if skill_count[b] > 0 else 0

        if prob_b_given_a >= 0.3:
            conditional[a].append((b, prob_b_given_a))
        if prob_a_given_b >= 0.3:
            conditional[b].append((a, prob_a_given_b))

    for skill in conditional:
        conditional[skill].sort(key=lambda x: -x[1])

    state.conditional = dict(conditional)


def _ensure_skill_embeddings_loaded(state: CoocState) -> dict[str, list[float]]:
    """Lazy-load skill embeddings cache into state."""
    if state.skill_embeddings is not None:
        return state.skill_embeddings

    if not _SKILL_EMBEDDINGS_PATH.exists():
        state.skill_embeddings = {}
        return state.skill_embeddings

    try:
        data = json.loads(_SKILL_EMBEDDINGS_PATH.read_text(encoding="utf-8"))
        state.skill_embeddings = data.get("skills", {})
    except Exception:
        state.skill_embeddings = {}

    return state.skill_embeddings


def infer_skills_cooccurrence(
    skills: list[str],
    state: CoocState,
    min_cooccurrence: float = 0.6,
    min_similarity: float = 0.85,
    max_inferred: int = 10,
) -> list[str]:
    """Co-occurrence based skill inference.

    Dual-filter: co-occurrence >= 0.6 AND embedding cosine >= 0.85
    Fallback: pure co-occurrence >= 0.80 when no embeddings

    Returns list of inferred skill names.
    """
    if not skills:
        return []

    _ensure_cooccurrence_loaded(state)
    embeddings = _ensure_skill_embeddings_loaded(state)
    use_embeddings = len(embeddings) > 0

    fallback_min_prob = 0.8 if not use_embeddings else min_cooccurrence

    user_lower = {s.lower() for s in skills if s}
    # name → (confidence, source, similarity)
    inferred: dict[str, tuple[float, str, float]] = {}

    for skill in skills:
        related = [
            (s, p)
            for s, p in state.conditional.get(skill, [])
            if p >= fallback_min_prob
        ]
        for related_skill, prob in related:
            if related_skill.lower() in user_lower:
                continue

            if use_embeddings:
                vec_a = embeddings.get(skill)
                vec_b = embeddings.get(related_skill)
                if vec_a is not None and vec_b is not None:
                    sim = max(0.0, _cosine_similarity(vec_a, vec_b))
                    if prob < min_cooccurrence or sim < min_similarity:
                        continue
                else:
                    # No embedding for one of them, use pure cooccurrence with higher threshold
                    if prob < 0.8:
                        continue
                    sim = 0.0
            else:
                sim = 0.0

            if related_skill not in inferred or prob > inferred[related_skill][0]:
                inferred[related_skill] = (prob, skill, sim)

    # Sort by confidence descending, return just names
    result = sorted(inferred.keys(), key=lambda n: -inferred[n][0])
    return result[:max_inferred]
