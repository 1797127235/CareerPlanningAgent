"""Multi-dimensional person-job matching service.

Four dimensions:
  1. 职业技能 (50%) — skill name + level weighted matching
  2. 发展潜力 (25%) — projects, awards, education quality
  3. 基础要求 (15%) — threshold: degree meets job level requirement
  4. 职业素养 (10%) — SJT soft skill scores vs job requirements
"""
from __future__ import annotations

_LEVEL_WEIGHT = {
    "advanced": 1.0,
    "intermediate": 0.75,
    "familiar": 0.5,
    "beginner": 0.25,
}

_DIMENSION_WEIGHTS = {
    "skill": 0.50,
    "potential": 0.25,
    "basic": 0.15,
    "soft_skill": 0.10,
}

_DEGREE_RANK = {
    "博士": 4, "硕士": 3, "本科": 2, "大专": 1, "专科": 1,
}

# career_level → minimum degree rank required
_LEVEL_DEGREE_REQ = {
    1: 1,  # 大专即可
    2: 2,  # 本科
    3: 2,  # 本科
    4: 3,  # 硕士优先
    5: 3,  # 硕士优先
}

_SJT_DIMS = ["communication", "learning", "collaboration", "innovation", "resilience"]


def compute_match(profile_data: dict, node: dict) -> dict:
    """Compute multi-dimensional match scores.

    Returns:
        {
            "total": 76,
            "dimensions": {
                "skill":      {"score": 72, "detail": "匹配 5/8 核心技能", "weight": 0.50},
                "potential":   {"score": 85, "detail": "2 个项目经历", "weight": 0.25},
                "basic":       {"score": 100, "detail": "学历达标", "weight": 0.15},
                "soft_skill":  {"score": 60, "detail": "未完成软技能评估", "weight": 0.10},
            }
        }
    """
    dims = {}

    # ── 1. 职业技能 ──────────────────────────────────────────────────────
    dims["skill"] = _score_skills(profile_data, node)

    # ── 2. 发展潜力 ──────────────────────────────────────────────────────
    dims["potential"] = _score_potential(profile_data)

    # ── 3. 基础要求 ──────────────────────────────────────────────────────
    dims["basic"] = _score_basic(profile_data, node)

    # ── 4. 职业素养 ──────────────────────────────────────────────────────
    dims["soft_skill"] = _score_soft_skills(profile_data, node)

    # ── Weighted total ───────────────────────────────────────────────────
    total = sum(
        dims[k]["score"] * _DIMENSION_WEIGHTS[k]
        for k in _DIMENSION_WEIGHTS
    )

    for k in dims:
        dims[k]["weight"] = _DIMENSION_WEIGHTS[k]

    return {"total": round(total), "dimensions": dims}


def _score_skills(profile_data: dict, node: dict) -> dict:
    """Weighted skill matching: considers both name match and skill level."""
    must_skills = node.get("must_skills", [])
    if not must_skills:
        return {"score": 0, "detail": "该岗位无技能要求数据"}

    user_skills = {}
    for s in profile_data.get("skills", []):
        if isinstance(s, dict) and s.get("name"):
            user_skills[s["name"].lower()] = s.get("level", "beginner")

    matched_count = 0
    weighted_sum = 0.0
    matched_names = []

    for ms in must_skills:
        ms_lower = ms.lower()
        if ms_lower in user_skills:
            level = user_skills[ms_lower]
            weight = _LEVEL_WEIGHT.get(level, 0.25)
            weighted_sum += weight
            matched_count += 1
            matched_names.append(ms)

    # Score: weighted match / total possible (each skill max 1.0)
    max_possible = len(must_skills) * 1.0
    score = round((weighted_sum / max_possible) * 100) if max_possible > 0 else 0

    if matched_count == 0:
        detail = f"未匹配到核心技能 (0/{len(must_skills)})"
    else:
        detail = f"匹配 {matched_count}/{len(must_skills)} 核心技能"

    return {"score": score, "detail": detail, "matched": matched_names}


def _score_potential(profile_data: dict) -> dict:
    """Development potential: projects + awards + education quality."""
    score = 0
    details = []

    # Projects
    projects = profile_data.get("projects", [])
    proj_count = len(projects)
    if proj_count == 0:
        proj_score = 0
    elif proj_count == 1:
        proj_score = 40
    elif proj_count == 2:
        proj_score = 60
    else:
        proj_score = 80
    score += proj_score
    if proj_count > 0:
        details.append(f"{proj_count} 个项目经历")

    # Awards
    awards = profile_data.get("awards", [])
    if awards:
        award_bonus = min(len(awards) * 10, 20)
        score += award_bonus
        details.append(f"{len(awards)} 项竞赛/荣誉")

    # Education bonus
    edu = profile_data.get("education", {})
    degree = edu.get("degree", "")
    if degree in ("硕士", "博士"):
        score += 10
        details.append(f"{degree}学历")

    score = min(score, 100)
    detail = "、".join(details) if details else "暂无项目和竞赛经历"

    return {"score": score, "detail": detail}


def _score_basic(profile_data: dict, node: dict) -> dict:
    """Three sub-scores: degree (40%) + major relevance (35%) + experience (25%)."""
    edu = profile_data.get("education", {})
    details = []

    # ── Sub 1: Degree (40%) ──
    degree = edu.get("degree", "")
    user_rank = _DEGREE_RANK.get(degree, 0)
    career_level = node.get("career_level", 2)
    required_rank = _LEVEL_DEGREE_REQ.get(career_level, 2)

    if user_rank == 0:
        degree_score = 50
        details.append("学历未填写")
    elif user_rank >= required_rank:
        degree_score = 100
        details.append("学历达标")
    else:
        degree_score = 40
        details.append("学历未达建议要求")

    # ── Sub 2: Major relevance (35%) ──
    user_major = edu.get("major", "").strip()
    related_majors = node.get("related_majors", [])

    if not user_major:
        major_score = 50
        details.append("专业未填写")
    elif not related_majors:
        major_score = 70
    else:
        # Check if user's major matches or partially matches any related major
        user_major_lower = user_major.lower()
        matched = False
        partial = False
        for rm in related_majors:
            rm_lower = rm.lower()
            if rm_lower == user_major_lower or rm_lower in user_major_lower or user_major_lower in rm_lower:
                matched = True
                break
        if not matched:
            # Fuzzy: check if any keywords overlap (e.g. "计算机" in "计算机科学与技术")
            for rm in related_majors:
                if any(kw in user_major for kw in rm[:2]) or any(kw in rm for kw in user_major[:2]):
                    partial = True
                    break

        if matched:
            major_score = 100
            details.append("专业对口")
        elif partial:
            major_score = 75
            details.append("专业相关")
        else:
            major_score = 40
            details.append("专业不太对口")

    # ── Sub 3: Experience (25%) ──
    user_exp = profile_data.get("experience_years", 0) or 0
    min_exp = node.get("min_experience", 0)

    if min_exp == 0:
        exp_score = 100  # No experience required
    elif user_exp >= min_exp:
        exp_score = 100
        details.append(f"经验达标({user_exp}年)")
    elif user_exp > 0:
        exp_score = round(user_exp / min_exp * 80)
        details.append(f"经验不足(需{min_exp}年)")
    else:
        exp_score = 30
        if min_exp > 0:
            details.append(f"需{min_exp}年经验")

    # Weighted total
    score = round(degree_score * 0.40 + major_score * 0.35 + exp_score * 0.25)
    detail = "、".join(details)

    return {"score": score, "detail": detail}


def _score_soft_skills(profile_data: dict, node: dict) -> dict:
    """Compare SJT assessment scores with job soft_skill requirements."""
    user_ss = profile_data.get("soft_skills", {})
    job_ss = node.get("soft_skills", {})

    if not job_ss:
        return {"score": 60, "detail": "该岗位无素养要求数据"}

    # Check if user has done SJT
    has_sjt = user_ss.get("_version") == 2 and any(
        user_ss.get(d) is not None for d in _SJT_DIMS
    )

    if not has_sjt:
        return {"score": 60, "detail": "未完成软技能评估，建议完成 SJT 测评"}

    # Compare each dimension
    total = 0
    count = 0
    for dim in _SJT_DIMS:
        job_req = job_ss.get(dim)
        user_val = user_ss.get(dim)
        if job_req is None or user_val is None:
            continue
        if isinstance(user_val, dict):
            user_score = user_val.get("score", 50)
        else:
            user_score = user_val

        # job_req is 1-5, convert to 0-100 scale
        req_score = job_req * 20
        # User's score is already 0-100 from SJT
        dim_score = min(user_score / req_score * 100, 100) if req_score > 0 else 100
        total += dim_score
        count += 1

    score = round(total / count) if count > 0 else 60
    detail = "基于 SJT 测评结果"

    return {"score": score, "detail": detail}
