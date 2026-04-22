# -*- coding: utf-8 -*-
"""Four-dimension scoring for career development reports."""
from __future__ import annotations

import json
from typing import Any

from backend.services.report.data import (
    _user_skill_set,
    _skill_proficiency,
    _PROFICIENCY_MULTIPLIER,
)


def _score_foundation(profile_data: dict, node: dict) -> int | None:
    """基础要求: education + experience match. Returns 0–100 or None."""
    scores = []

    # Education: check profile_json.education.major vs node.related_majors
    education = profile_data.get("education") or {}
    major = ""
    if isinstance(education, dict):
        major = (education.get("major") or "").lower().strip()
    elif isinstance(education, str):
        major = education.lower().strip()

    related_majors = [m.lower() for m in (node.get("related_majors") or [])]
    if major and related_majors:
        # Check if user major is in (or overlaps) the related majors
        is_match = any(major in rm or rm in major for rm in related_majors)
        scores.append(100 if is_match else 50)
    elif related_majors:
        # No major info → give neutral score
        scores.append(60)

    # Experience: compare profile_json.experience_years vs node.min_experience
    exp_years = profile_data.get("experience_years")
    min_exp = node.get("min_experience")
    if exp_years is not None and min_exp is not None:
        try:
            exp_f = float(exp_years)
            min_f = float(min_exp)
            if exp_f >= min_f:
                scores.append(100)
            elif min_f > 0:
                scores.append(max(0, int(exp_f / min_f * 100)))
            else:
                scores.append(100)
        except (TypeError, ValueError):
            pass

    if not scores:
        return None
    return int(sum(scores) / len(scores))


def _score_skills(
    profile_data: dict,
    node: dict,
    practiced: set[str] | None = None,
    completed_practiced: set[str] | None = None,
) -> int:
    """
    职业技能: weighted skill-tier match with three-tier proficiency multiplier.

    Multipliers (only applied when project data exists):
      completed project  → 1.2×  (实战完成)
      any project usage  → 1.0×  (项目使用)
      resume-only claim  → 0.7×  (仅简历声称)
      no project data    → 1.0×  (fallback, no penalty for fresh students)
    """
    user_skills = _user_skill_set(profile_data)
    practiced = practiced or set()
    completed_practiced = completed_practiced or set()
    has_project_data = bool(practiced or completed_practiced)

    tiers = node.get("skill_tiers") or {}
    core      = tiers.get("core")      or []
    important = tiers.get("important") or []
    bonus     = tiers.get("bonus")     or []

    tier_pairs = [(core, 1.0), (important, 0.6), (bonus, 0.3)]
    total_w = sum(len(t) * w for t, w in tier_pairs)
    if total_w == 0:
        return 0

    matched_w = 0.0
    for tier_list, base_w in tier_pairs:
        for e in tier_list:
            is_matched, status = _skill_proficiency(
                e.get("name", ""), user_skills, practiced, completed_practiced, has_project_data
            )
            if is_matched:
                multiplier = _PROFICIENCY_MULTIPLIER.get(status or "claimed", 1.0)
                matched_w += base_w * multiplier

    return min(100, int(matched_w / total_w * 100))


def _score_qualities(mock_sessions: list) -> int | None:
    """职业素养: average of interview dimension scores. None if no data."""
    if not mock_sessions:
        return None

    dim_scores: list[float] = []
    for session in mock_sessions:
        # Try mapped_dimensions first (structured per-dim scores)
        mapped_raw = getattr(session, "mapped_dimensions", None)
        if mapped_raw:
            try:
                dims = json.loads(mapped_raw)
                if isinstance(dims, dict):
                    for v in dims.values():
                        if isinstance(v, (int, float)) and 0 <= v <= 100:
                            dim_scores.append(float(v))
            except Exception:
                pass

        # Fallback: analysis_json overall rating → rough heuristic
        if not dim_scores:
            analysis_raw = getattr(session, "analysis_json", None)
            if analysis_raw:
                try:
                    analysis = json.loads(analysis_raw)
                    if isinstance(analysis, dict):
                        overall = analysis.get("overall", "")
                        strengths = analysis.get("strengths", [])
                        weaknesses = analysis.get("weaknesses", [])
                        if isinstance(strengths, list) and isinstance(weaknesses, list):
                            s_cnt = len(strengths)
                            w_cnt = len(weaknesses)
                            total = s_cnt + w_cnt
                            if total > 0:
                                dim_scores.append(s_cnt / total * 100)
                except Exception:
                    pass

    if not dim_scores:
        return None
    return min(100, int(sum(dim_scores) / len(dim_scores)))


def _score_potential(
    snapshots: list,
    projects: list,
    transition_probability: float,
) -> int:
    """发展潜力: readiness trend + completed projects + transition_probability."""
    scores: list[float] = []

    # 1. Readiness trend (slope across last 4+ snapshots)
    if len(snapshots) >= 2:
        recent = sorted(snapshots, key=lambda s: s.created_at)[-4:]
        values = [float(s.readiness_score) for s in recent]
        if len(values) >= 2:
            # Simple linear trend: compare first half avg vs second half avg
            mid = len(values) // 2
            avg_early = sum(values[:mid]) / mid
            avg_late = sum(values[mid:]) / (len(values) - mid)
            delta = avg_late - avg_early
            # delta > 0 → growing; normalize to 0-100
            trend_score = min(100, max(0, 50 + delta * 2))  # ±25 range maps to 0-100
            scores.append(trend_score)
    elif len(snapshots) == 1:
        scores.append(50.0)  # baseline — no trend data yet

    # 2. Completed projects (capped at 3 for scoring)
    # Only score if user has at least one project — otherwise 0 projects = no data, not a penalty
    if projects:
        completed_count = sum(1 for p in projects if getattr(p, "status", "") == "completed")
        project_score = min(100, completed_count * 33)
        scores.append(float(project_score))

    # 3. Transition probability from CareerGoal (already 0.0–1.0 or 0–100)
    if transition_probability:
        prob = transition_probability
        if prob <= 1.0:
            prob *= 100
        scores.append(min(100.0, float(prob)))

    if not scores:
        return 50  # fallback neutral score
    return int(sum(scores) / len(scores))


def _weighted_match_score(four_dim: dict) -> int:
    """Compute overall match score from four dimensions. Weights: skills=40%, potential=25%, foundation=20%, qualities=15%."""
    weights = {
        "skills": 0.40,
        "potential": 0.25,
        "foundation": 0.20,
        "qualities": 0.15,
    }
    total_w = 0.0
    total_score = 0.0
    for key, w in weights.items():
        val = four_dim.get(key)
        if val is not None:
            total_score += val * w
            total_w += w
    if total_w == 0:
        return 0
    return int(total_score / total_w)
