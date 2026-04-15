# -*- coding: utf-8 -*-
"""Profile scorer — seven-dimension and four-dimension scoring."""
from __future__ import annotations

import json
import math
import re
from typing import Any

from backend.services.profile.shared import (
    _DEGREE_RANK,
    _LEVEL_WEIGHT,
    _PROFICIENCY_WEIGHT,
    _STAGE_WEIGHTS,
    _DEFAULT_SSW,
    _RANK_DEPTH_MULTIPLIER,
    _DIRECTION_TO_GRAPH_NODE,
    _clamp01,
    _user_skill_map,
    _user_cert_set,
    _user_competency_names,
)
from backend.services.profile import sjt


def compute_idf_cross_direction(profiles: dict[str, Any]) -> dict[str, float]:
    """Compute cross-direction IDF for each skill.

    IDF(skill) = log(N / (1 + df))
    """
    n_directions = len(profiles)
    doc_freq: dict[str, int] = {}
    for direction in profiles.values():
        stg = direction.get("skill_type_groups", {})
        seen_skills: set[str] = set()
        for group in (
            (stg.get("hard_skill") or [])
            + (stg.get("knowledge") or [])
            + (stg.get("soft_skill") or [])
        ):
            if isinstance(group, dict):
                name = (group.get("skill") or group.get("name") or "").strip().lower()
                if name and name not in seen_skills:
                    seen_skills.add(name)
                    doc_freq[name] = doc_freq.get(name, 0) + 1

    return {
        skill: math.log(n_directions / (1 + df))
        for skill, df in doc_freq.items()
    }


def _score_skill_coverage(
    user_skills: dict[str, dict],
    direction: dict[str, Any],
    idf: dict[str, float],
) -> tuple[float, dict]:
    """Dimension 1: Skill coverage — TF-IDF weighted coverage ratio."""
    stg = direction.get("skill_type_groups", {})
    required_skills = (stg.get("hard_skill") or []) + (stg.get("knowledge") or [])
    if not required_skills:
        required_skills = direction.get("top_skills", [])

    if not required_skills:
        return 0.5, {"detail": "该方向无技能数据", "matched": [], "missing": []}

    jd_count = max(direction.get("jd_count", 1), 1)
    total_weight = 0.0
    matched_weight = 0.0
    matched_list: list[str] = []
    missing_list: list[dict] = []

    for skill_entry in required_skills[:15]:
        if not isinstance(skill_entry, dict):
            continue
        skill_name = (skill_entry.get("skill") or skill_entry.get("name") or "").strip()
        if not skill_name:
            continue
        count = skill_entry.get("count", 0) or 0
        tf = count / jd_count
        skill_idf = idf.get(skill_name.lower(), 1.0)
        tfidf = tf * skill_idf
        total_weight += tfidf

        if skill_name.lower() in user_skills:
            matched_weight += tfidf
            matched_list.append(skill_name)
        else:
            missing_list.append({
                "name": skill_name,
                "frequency": round(tf, 3),
                "idf": round(skill_idf, 2),
                "tfidf": round(tfidf, 3),
            })

    score = matched_weight / total_weight if total_weight > 0 else 0.0
    return round(min(score, 1.0), 3), {
        "matched": matched_list,
        "missing": missing_list[:8],
    }


def _score_skill_depth(
    user_skills: dict[str, dict],
    direction: dict[str, Any],
) -> tuple[float, dict]:
    """Dimension 2: Skill depth — user level vs JD proficiency requirements."""
    stg = direction.get("skill_type_groups", {})
    required_skills = (stg.get("hard_skill") or []) + (stg.get("knowledge") or [])
    if not required_skills:
        return 0.5, {"detail": "无技能数据"}

    depth_scores: list[float] = []
    rank_weights: list[float] = []
    details: list[dict] = []

    for skill_entry in required_skills[:15]:
        if not isinstance(skill_entry, dict):
            continue
        skill_name = (skill_entry.get("skill") or skill_entry.get("name") or "").strip()
        if not skill_name or skill_name.lower() not in user_skills:
            continue

        user_info = user_skills[skill_name.lower()]
        user_level_w = _LEVEL_WEIGHT.get(user_info.get("level", "intermediate"), 0.5)

        # JD required average proficiency
        prof_dist = skill_entry.get("proficiency_dist", {})
        unspecified_ratio = 0.0
        if prof_dist:
            total_cnt = sum(prof_dist.values())
            if total_cnt > 0:
                unspecified_cnt = prof_dist.get("不限", 0)
                unspecified_ratio = unspecified_cnt / total_cnt
                required_w = sum(
                    _PROFICIENCY_WEIGHT.get(level, 0.3) * cnt
                    for level, cnt in prof_dist.items()
                ) / total_cnt
            else:
                required_w = 0.3
        else:
            required_w = 0.3

        if unspecified_ratio > 0.8:
            raw_score = user_level_w
        else:
            ratio = min(user_level_w / max(required_w, 0.1), 1.5)
            raw_score = min(ratio, 1.0)

        # Default rank=1 (no ESCO dependency in service layer)
        rank = 1
        weight = _RANK_DEPTH_MULTIPLIER.get(rank, 0.6)

        depth_scores.append(raw_score * weight)
        rank_weights.append(weight)
        details.append({
            "skill": skill_name,
            "user_level": user_info.get("level", "?"),
            "required_avg": round(required_w, 2),
            "rank": rank,
        })

    if not depth_scores:
        return 0.0, {"skills_compared": 0, "details": []}

    total_weight = sum(rank_weights)
    score = sum(depth_scores) / total_weight if total_weight > 0 else 0.0
    return round(score, 3), {"skills_compared": len(depth_scores), "details": details[:5]}


def _score_experience(
    profile: dict[str, Any],
    direction: dict[str, Any],
) -> tuple[float, dict]:
    """Dimension 3: Experience match — user years vs JD percentiles."""
    exp_data = direction.get("experience", {}).get("years", {})
    p25 = exp_data.get("p25")
    p50 = exp_data.get("p50")
    p75 = exp_data.get("p75")

    # Calculate user experience years
    user_years = 0.0
    for intern in profile.get("internships", []):
        dur = intern.get("duration", "")
        if isinstance(dur, (int, float)):
            user_years += dur / 12.0
        elif isinstance(dur, str) and dur:
            m = re.search(r"(\d+)", dur)
            if m:
                num = int(m.group(1))
                if "年" in dur:
                    user_years += num
                else:
                    user_years += num / 12.0
    for we in profile.get("work_experiences", []):
        dur = we.get("duration", "")
        if isinstance(dur, (int, float)):
            user_years += dur / 12.0
        elif isinstance(dur, str) and dur:
            m = re.search(r"(\d+)", dur)
            if m:
                num = int(m.group(1))
                if "年" in dur:
                    user_years += num
                else:
                    user_years += num / 12.0
    # Support 'experience' key with duration_months
    for we in profile.get("experience", []):
        if isinstance(we, dict):
            dur = we.get("duration_months", 0)
            if isinstance(dur, (int, float)):
                user_years += dur / 12.0

    if p50 is None:
        return 0.5, {"detail": "该方向无经验数据", "user_years": round(user_years, 1)}

    p50 = float(p50)
    if p50 <= 0:
        level_dist = direction.get("experience", {}).get("level_dist", {})
        total_levels = sum(level_dist.values()) if level_dist else 0
        if total_levels > 0:
            senior = level_dist.get("senior", 0)
            mid = level_dist.get("mid", 0)
            experienced_ratio = (mid + senior) / total_levels
            if user_years >= 2:
                score = 1.0
            elif user_years >= 1:
                score = 0.7 + 0.3 * (1 - experienced_ratio)
            else:
                score = 0.5 + 0.3 * (1 - experienced_ratio)
        else:
            score = 0.8
    elif user_years >= p50:
        score = min(1.0, 0.8 + 0.2 * min(user_years / max(p50, 0.1), 2.0))
    else:
        score = max(0.1, user_years / max(p50, 0.1)) * 0.8

    return round(score, 3), {
        "user_years": round(user_years, 1),
        "required_p50": p50,
        "required_p25": p25,
    }


def _score_education(
    profile: dict[str, Any],
    direction: dict[str, Any],
) -> tuple[float, dict]:
    """Dimension 4: Education match — user degree vs JD distribution."""
    edu_dist = direction.get("education_dist", {})
    if not edu_dist:
        return 0.5, {"detail": "该方向无学历数据"}

    user_degree = (
        profile.get("basic_info", {}).get("degree", "")
        or profile.get("basic_info", {}).get("education", "")
        or profile.get("degree", "")
    ).strip()
    user_rank = _DEGREE_RANK.get(user_degree, 2)

    total = sum(edu_dist.values())
    if total <= 0:
        return 0.5, {"detail": "学历数据为空"}

    required_avg_rank = sum(
        _DEGREE_RANK.get(deg, 2) * cnt for deg, cnt in edu_dist.items()
    ) / total

    if user_rank >= required_avg_rank:
        score = 1.0
    else:
        score = max(0.2, user_rank / max(required_avg_rank, 1))

    return round(score, 3), {
        "user_degree": user_degree or "未填写",
        "user_rank": user_rank,
        "required_avg_rank": round(required_avg_rank, 1),
        "distribution": edu_dist,
    }


def _score_practice(
    profile: dict[str, Any],
    direction: dict[str, Any],
) -> tuple[float, dict]:
    """Dimension 5: Practice depth — project + internship count."""
    project_count = len(profile.get("projects", []))
    intern_count = len(profile.get("internships", []))
    work_count = len(profile.get("work_experiences", []))
    exp_count = len(profile.get("experience", []))
    total_practice = project_count + intern_count + work_count + exp_count

    level_dist = direction.get("experience", {}).get("level_dist", {})
    senior_ratio = level_dist.get("senior", 0)
    mid_ratio = level_dist.get("mid", 0)
    total_levels = senior_ratio + mid_ratio + level_dist.get("junior", 0)

    if total_levels > 0:
        expected_practice = 2 + (senior_ratio + mid_ratio) / total_levels * 4
    else:
        expected_practice = 3

    score = min(1.0, total_practice / max(expected_practice, 1))
    return round(score, 3), {
        "projects": project_count,
        "internships": intern_count,
        "work_experiences": work_count + exp_count,
        "expected": round(expected_practice, 1),
    }


def _score_certificates(
    user_certs: set[str],
    direction: dict[str, Any],
) -> tuple[float, dict]:
    """Dimension 6: Certificate match."""
    dir_certs = direction.get("certificates", [])
    if not dir_certs:
        return 1.0, {"detail": "该方向无证书要求", "matched": [], "missing": []}

    dir_cert_names: list[str] = []
    for c in dir_certs:
        name = c.get("name", "") if isinstance(c, dict) else str(c)
        if name.strip():
            dir_cert_names.append(name.strip())

    if not dir_cert_names:
        return 1.0, {"detail": "该方向无证书要求", "matched": [], "missing": []}

    matched = [c for c in dir_cert_names if c.lower() in user_certs]
    missing = [c for c in dir_cert_names if c.lower() not in user_certs]

    score = len(matched) / len(dir_cert_names)
    return round(score, 3), {"matched": matched, "missing": missing}


def _score_competency(
    user_competencies: set[str],
    direction: dict[str, Any],
    graph_node: dict[str, Any] | None = None,
) -> tuple[float, dict]:
    """Dimension 7: Competency match — user competencies vs soft_skills."""
    soft_skills: list[str] = []
    if graph_node:
        soft_skills = graph_node.get("soft_skills", [])
    if not soft_skills:
        stg = direction.get("skill_type_groups", {})
        for s in (stg.get("soft_skill") or [])[:5]:
            name = s.get("skill") or s.get("name") or ""
            if name.strip():
                soft_skills.append(name.strip())

    if not soft_skills:
        return 0.5, {"detail": "该方向无素质要求"}

    matched: list[str] = []
    missing: list[str] = []
    for soft in soft_skills:
        if any(soft in comp or comp in soft for comp in user_competencies):
            matched.append(soft)
        else:
            missing.append(soft)

    score = len(matched) / len(soft_skills) if soft_skills else 0.5
    return round(score, 3), {"matched": matched, "missing": missing}


def _compute_weights(direction: dict[str, Any]) -> dict[str, float]:
    """Auto-derive dimension weights from JD data distribution."""
    stg = direction.get("skill_type_groups", {})
    hard_mentions = sum(s.get("count", 0) for s in (stg.get("hard_skill") or []))
    soft_mentions = sum(s.get("count", 0) for s in (stg.get("soft_skill") or []))
    knowledge_mentions = sum(s.get("count", 0) for s in (stg.get("knowledge") or []))
    total_mentions = hard_mentions + soft_mentions + knowledge_mentions

    if total_mentions <= 0:
        return {
            "skill_coverage": 0.25, "skill_depth": 0.15,
            "experience": 0.15, "education": 0.10,
            "practice": 0.15, "certificates": 0.05,
            "competency": 0.15,
        }

    hard_ratio = hard_mentions / total_mentions
    soft_ratio = soft_mentions / total_mentions

    exp_p50 = (direction.get("experience", {}).get("years", {}).get("p50") or 0)
    exp_boost = min(0.10, float(exp_p50) * 0.03)

    cert_count = len(direction.get("certificates", []))
    cert_boost = min(0.08, cert_count * 0.03)

    raw = {
        "skill_coverage": 0.15 + hard_ratio * 0.20,
        "skill_depth": 0.10 + hard_ratio * 0.10,
        "experience": 0.10 + exp_boost,
        "education": 0.08,
        "practice": 0.12,
        "certificates": 0.03 + cert_boost,
        "competency": 0.08 + soft_ratio * 0.10,
    }

    total = sum(raw.values())
    return {k: round(v / total, 3) for k, v in raw.items()}


def _infer_career_stage(profile: dict[str, Any], dims: dict) -> str:
    """Infer career stage from 7-dim results."""
    user_years = dims.get("experience", {}).get("detail", {}).get("user_years", 0)
    if user_years <= 2:
        return "entry"
    elif user_years <= 7:
        return "mid"
    return "senior"


def _score_basic(dims: dict) -> tuple[float, dict]:
    """Basic requirements = education(0.30) + certificates(0.20) + experience(0.50)."""
    s_edu = dims["education"]["score"] / 100.0
    s_cert = dims["certificates"]["score"] / 100.0
    s_exp = dims["experience"]["score"] / 100.0
    score = 0.30 * s_edu + 0.20 * s_cert + 0.50 * s_exp
    return score, {
        "education": round(s_edu * 100, 1),
        "certificates": round(s_cert * 100, 1),
        "experience": round(s_exp * 100, 1),
    }


def _score_skills_agg(dims: dict) -> tuple[float, dict]:
    """Professional skills = coverage(0.40) + depth(0.35) + practice(0.25)."""
    s_cov = dims["skill_coverage"]["score"] / 100.0
    s_dep = dims["skill_depth"]["score"] / 100.0
    s_pra = dims["practice"]["score"] / 100.0
    score = 0.40 * s_cov + 0.35 * s_dep + 0.25 * s_pra
    return score, {
        "coverage": round(s_cov * 100, 1),
        "depth": round(s_dep * 100, 1),
        "practice": round(s_pra * 100, 1),
    }


def _score_qualities(
    user_profile: dict[str, Any],
    graph_node: dict[str, Any] | None,
    sjt_scores: dict[str, float] | None,
) -> tuple[float, dict]:
    """Professional qualities — 3 sub-dimensions weighted by job soft_skill_weights."""
    ssw = (graph_node or {}).get("soft_skill_weights") or {}
    # Fallback: if old 5-dim weights or empty, use default 3-dim
    dims_v2 = ["communication", "learning", "collaboration"]
    if not all(d in ssw for d in dims_v2):
        ssw = _DEFAULT_SSW.copy()

    user_soft = user_profile.get("soft_skills", {})

    sub_scores: dict[str, float] = {}
    for dim in dims_v2:
        job_weight = ssw.get(dim, 0.33)

        # User score from soft_skills dict (v2 format)
        user_val = user_soft.get(dim)
        if isinstance(user_val, dict):
            user_score = user_val.get("score", 0) / 100.0
        elif isinstance(user_val, (int, float)):
            user_score = user_val / 100.0
        else:
            user_score = 0  # Not assessed yet

        # Match: user / job_requirement, capped at 1.0
        if job_weight > 0.05:
            match = _clamp01(user_score / job_weight)
        else:
            match = _clamp01(user_score)

        sub_scores[dim] = round(match * 100, 1)

    # Weighted average by job weights
    total_w = sum(ssw.get(d, 0.33) for d in dims_v2)
    if total_w > 0:
        score = sum(sub_scores[d] / 100.0 * ssw.get(d, 0.33) for d in dims_v2) / total_w
    else:
        score = sum(sub_scores[d] for d in dims_v2) / (100.0 * len(dims_v2))

    return score, {d: sub_scores[d] for d in dims_v2}


def _score_potential(
    direction: dict[str, Any],
    role_family: str,
) -> tuple[float, dict]:
    """Development potential — salary_growth + skill_growth + promotion + outlook.

    Returns neutral scores (0.5) since market signal DB queries are deferred.
    """
    s_salary = 0.5
    s_skill = 0.5

    # Promotion space from level distribution
    level_dist = direction.get("experience", {}).get("level_dist", {})
    total_levels = sum(level_dist.values()) or 1
    senior_ratio = level_dist.get("senior", 0) / total_levels
    exp_years = direction.get("experience", {}).get("years", {})
    p25 = exp_years.get("p25", 1) or 1
    p75 = exp_years.get("p75", 3) or 3
    spread = p75 / max(p25, 0.5)
    s_promotion = _clamp01(0.5 * min(1.0, senior_ratio * 3) + 0.5 * min(1.0, spread / 5))

    s_outlook = 0.5

    score = 0.30 * s_salary + 0.25 * s_skill + 0.20 * s_promotion + 0.25 * s_outlook

    return score, {
        "salary_growth": round(s_salary * 100, 1),
        "skill_growth": round(s_skill * 100, 1),
        "promotion_space": round(s_promotion * 100, 1),
        "industry_outlook": round(s_outlook * 100, 1),
    }


def compute_quality(profile_data: dict) -> dict:
    """Deterministic quality scoring from profile data.

    Returns dict with ``completeness``, ``competitiveness``, and
    ``dimensions`` (soft-skill entries if present).
    """
    _QUALITY_LEVEL_WEIGHT = {
        "expert": 1.0, "advanced": 1.0,
        "proficient": 0.7, "intermediate": 0.7,
        "familiar": 0.3, "beginner": 0.1,
    }

    skills = profile_data.get("skills", [])
    knowledge_areas = profile_data.get("knowledge_areas", [])
    projects = profile_data.get("projects", [])
    has_education = bool(profile_data.get("education"))
    has_experience = profile_data.get("experience_years", 0) > 0

    # Completeness: are the sections filled?
    completeness = min(1.0, (
        (0.3 if skills else 0)
        + (0.2 if knowledge_areas else 0)
        + (0.2 if has_experience else 0)
        + (0.2 if has_education else 0)
        + (0.1 if projects else 0)
    ))

    # Competitiveness: weighted skill depth + breadth + experience
    skill_score = sum(
        _QUALITY_LEVEL_WEIGHT.get(s.get("level", "beginner"), 0.1)
        for s in skills
    )
    skill_component = min(0.4, skill_score * 0.04)
    breadth_component = min(0.2, len(knowledge_areas) * 0.03)
    project_component = min(0.15, len(projects) * 0.05)
    experience_component = min(
        0.15, profile_data.get("experience_years", 0) * 0.05
    )
    education_component = 0.1 if has_education else 0

    raw_competitiveness = (
        skill_component + breadth_component + project_component
        + experience_component + education_component
    )
    # Ensure minimum baseline for non-empty profiles, cap at 1.0
    competitiveness = min(1.0, max(raw_competitiveness, 0.05 if skills else 0))

    # Extract soft skill dimensions if present
    soft = profile_data.get("soft_skills", {})
    dimensions: list[dict] = []
    if soft.get("_version") == 2:
        dim_labels = {
            "communication": "沟通能力",
            "learning": "学习能力",
            "collaboration": "协作能力",
        }
    else:
        dim_labels = {
            "innovation": "创新能力",
            "learning": "学习能力",
            "resilience": "抗压能力",
            "communication": "沟通能力",
            "internship": "实习能力",
        }
    for key, label in dim_labels.items():
        val = soft.get(key)
        if isinstance(val, dict):
            score = val.get("score", 50)
        elif isinstance(val, (int, float)):
            score = val
        else:
            continue
        dimensions.append({"key": key, "label": label, "score": int(score)})

    return {
        "completeness": round(completeness, 2),
        "competitiveness": round(competitiveness, 2),
        "dimensions": dimensions,
    }


def score_four_dimensions(
    profile: dict,
    target_node: dict,
    cross_direction_idf: dict[str, float],
    profiles: dict[str, Any] | None = None,
    db_session: Any = None,
    sjt_scores: dict[str, float] | None = None,
) -> dict:
    """Four-dimension scoring.

    Builds on seven-dimension scoring, then aggregates:
      basic = edu(0.30) + cert(0.20) + exp(0.50)
      skills = coverage(0.40) + depth(0.35) + practice(0.25)
      qualities = 3 sub-dimensions (communication/learning/collaboration) weighted by soft_skill_weights
      potential = salary + skill_growth + promotion + outlook

    AHP stage weights: entry/mid/senior (from _STAGE_WEIGHTS)
    Basic score threshold penalty: if s_basic < 0.4, penalty = 0.7 + 0.3 * (s_basic / 0.4)

    Returns:
        {total_score, career_stage, four_dimensions: {basic, skills, qualities, potential}}
    """
    if profiles is None:
        profiles = {}

    # Find matching direction in profiles.json
    node_id = target_node.get("node_id", "")

    # Try direct match, then label match, then mapping
    direction = profiles.get(node_id)
    if not direction:
        label = target_node.get("label", "")
        direction = profiles.get(label)
    if not direction:
        # Try reverse mapping
        for onet_id, graph_id in _DIRECTION_TO_GRAPH_NODE.items():
            if graph_id == node_id or graph_id == target_node.get("label", ""):
                direction = profiles.get(onet_id)
                if direction:
                    break

    # If no profiles data, create a minimal one from graph node
    if not direction:
        direction = sjt.direction_from_node(target_node)

    user_skills = _user_skill_map(profile)
    user_certs = _user_cert_set(profile)
    user_comps = _user_competency_names(profile)
    weights = _compute_weights(direction)

    # Compute seven dimensions
    dim_results: dict[str, dict] = {}
    scorers = [
        ("skill_coverage", lambda: _score_skill_coverage(user_skills, direction, cross_direction_idf)),
        ("skill_depth", lambda: _score_skill_depth(user_skills, direction)),
        ("experience", lambda: _score_experience(profile, direction)),
        ("education", lambda: _score_education(profile, direction)),
        ("practice", lambda: _score_practice(profile, direction)),
        ("certificates", lambda: _score_certificates(user_certs, direction)),
        ("competency", lambda: _score_competency(user_comps, direction, target_node)),
    ]

    for dim_name, scorer_fn in scorers:
        score, detail = scorer_fn()
        weight = weights[dim_name]
        dim_results[dim_name] = {
            "score": round(score * 100, 1),
            "weight": weight,
            "weighted_score": round(score * weight * 100, 1),
            "detail": detail,
        }

    # Infer career stage
    stage = _infer_career_stage(profile, dim_results)
    stage_weights = _STAGE_WEIGHTS[stage]

    # Compute 4 dimensions
    s_basic, sub_basic = _score_basic(dim_results)
    s_skills, sub_skills = _score_skills_agg(dim_results)
    s_qualities, sub_qualities = _score_qualities(profile, target_node, sjt_scores)

    role_family = target_node.get("role_family", "")
    s_potential, sub_potential = _score_potential(direction, role_family)

    # Basic threshold penalty
    if s_basic < 0.4:
        penalty = 0.7 + 0.3 * (s_basic / 0.4)
    else:
        penalty = 1.0

    # Weighted total
    total = penalty * (
        stage_weights["basic"] * s_basic
        + stage_weights["skills"] * s_skills
        + stage_weights["qualities"] * s_qualities
        + stage_weights["potential"] * s_potential
    )

    return {
        "total_score": round(total * 100, 1),
        "career_stage": stage,
        "stage_weights": stage_weights,
        "basic_penalty_applied": penalty < 1.0,
        "four_dimensions": {
            "basic": {
                "score": round(s_basic * 100, 1),
                "weight": stage_weights["basic"],
                "sub": sub_basic,
            },
            "skills": {
                "score": round(s_skills * 100, 1),
                "weight": stage_weights["skills"],
                "sub": sub_skills,
            },
            "qualities": {
                "score": round(s_qualities * 100, 1),
                "weight": stage_weights["qualities"],
                "sub": sub_qualities,
            },
            "potential": {
                "score": round(s_potential * 100, 1),
                "weight": stage_weights["potential"],
                "sub": sub_potential,
            },
        },
    }
