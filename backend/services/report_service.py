"""
Report service — generates career development reports.

Four-dimension scoring pipeline:
  基础要求  — education + experience match vs job requirements
  职业技能  — weighted skill-tier match (reuses growth_log formula)
  职业素养  — mock interview dimension averages (None if no data)
  发展潜力  — readiness trend slope + project count + transition_probability

Data sources:
  Profile.profile_json        → skills, education, experience_years
  CareerGoal                  → target_node_id, gap_skills, transition_probability
  GrowthSnapshot[]            → readiness curve
  MockInterviewSession[]      → interview dimension scores
  ProjectRecord[]             → completed projects
  data/graph.json             → promotion_path, skill_tiers, career_ceiling, etc.
  data/market_signals.json    → demand_change_pct, salary_cagr, timing
  data/level_skills.json      → per-level skill lists (optional, for action plan)
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Project root = two levels up from this file (backend/services/report_service.py)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"

# ── Static data (loaded once per process) ─────────────────────────────────────

_GRAPH_NODES: dict[str, dict] = {}
_LEVEL_SKILLS: dict[str, dict] = {}
_MARKET: dict[str, dict] = {}        # family_name → signal dict
_NODE_TO_FAMILY: dict[str, str] = {} # node_id → family_name


def _load_static() -> None:
    global _GRAPH_NODES, _LEVEL_SKILLS, _MARKET, _NODE_TO_FAMILY
    if _GRAPH_NODES:
        return

    try:
        raw = json.loads((_DATA_DIR / "graph.json").read_text(encoding="utf-8"))
        _GRAPH_NODES = {n["node_id"]: n for n in raw.get("nodes", [])}
    except Exception as e:
        logger.warning("graph.json load failed: %s", e)

    try:
        _LEVEL_SKILLS = json.loads((_DATA_DIR / "level_skills.json").read_text(encoding="utf-8"))
    except Exception:
        pass  # optional — fallback to gap_skills

    try:
        raw_market = json.loads((_DATA_DIR / "market_signals.json").read_text(encoding="utf-8"))
        _MARKET = raw_market if isinstance(raw_market, dict) else {}
        for family, info in _MARKET.items():
            for nid in info.get("node_ids", []):
                _NODE_TO_FAMILY[nid] = family
    except Exception as e:
        logger.warning("market_signals.json load failed: %s", e)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_profile(profile_json: str) -> dict:
    try:
        return json.loads(profile_json or "{}")
    except Exception:
        return {}


def _user_skill_set(profile_data: dict) -> set[str]:
    raw = profile_data.get("skills", [])
    if not raw:
        return set()
    if isinstance(raw[0], dict):
        return {s.get("name", "").lower().strip() for s in raw if s.get("name")}
    return {s.lower().strip() for s in raw if isinstance(s, str) and s.strip()}


def _skill_matches(skill_name: str, user_skills: set[str]) -> bool:
    """Reuse same matching logic as growth_log_service."""
    def _norm(s: str) -> str:
        return s.lower().strip().replace(" ", "").replace("-", "").replace("_", "")

    name = skill_name.lower().strip()
    name_norm = _norm(skill_name)
    if not name:
        return False
    if name in user_skills:
        return True
    if len(name_norm) <= 2:
        return False
    for us in user_skills:
        if not us:
            continue
        us_norm = _norm(us)
        if name_norm == us_norm:
            return True
        if len(us_norm) > 2 and (name_norm in us_norm or us_norm in name_norm):
            return True
    return False


# ── Four-dimension scoring ─────────────────────────────────────────────────────

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


def _score_skills(profile_data: dict, node: dict) -> int:
    """职业技能: weighted skill-tier match (same formula as growth_log_service)."""
    user_skills = _user_skill_set(profile_data)
    tiers = node.get("skill_tiers") or {}
    core = tiers.get("core") or []
    important = tiers.get("important") or []
    bonus = tiers.get("bonus") or []

    total_w = len(core) * 1.0 + len(important) * 0.6 + len(bonus) * 0.3
    if total_w == 0:
        return 0

    matched_w = 0.0
    for e in core:
        if _skill_matches(e.get("name", ""), user_skills):
            matched_w += 1.0
    for e in important:
        if _skill_matches(e.get("name", ""), user_skills):
            matched_w += 0.6
    for e in bonus:
        if _skill_matches(e.get("name", ""), user_skills):
            matched_w += 0.3

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


# ── Skill gap analysis ────────────────────────────────────────────────────────

def _build_skill_gap(profile_data: dict, node: dict) -> dict:
    """
    Build market-oriented skill gap analysis using JD frequency data from skill_tiers.

    Returns:
      core / important / bonus  — tier coverage stats {total, matched, pct}
      top_missing               — up to 8 missing skills sorted by JD freq desc
      positioning               — market positioning label (初级/中级/资深)
    """
    user_skills = _user_skill_set(profile_data)
    tiers = node.get("skill_tiers") or {}
    core      = tiers.get("core")      or []
    important = tiers.get("important") or []
    bonus     = tiers.get("bonus")     or []

    def _tier_stats(skills: list) -> dict:
        total   = len(skills)
        matched = sum(1 for s in skills if _skill_matches(s.get("name", ""), user_skills))
        return {"total": total, "matched": matched, "pct": int(matched / total * 100) if total else 0}

    core_stats      = _tier_stats(core)
    important_stats = _tier_stats(important)
    bonus_stats     = _tier_stats(bonus)

    # Collect missing skills with JD frequency + tier label
    missing: list[dict] = []
    for s in core:
        if not _skill_matches(s.get("name", ""), user_skills):
            missing.append({"name": s.get("name", ""), "freq": s.get("freq", 0), "tier": "core"})
    for s in important:
        if not _skill_matches(s.get("name", ""), user_skills):
            missing.append({"name": s.get("name", ""), "freq": s.get("freq", 0), "tier": "important"})
    for s in bonus:
        if not _skill_matches(s.get("name", ""), user_skills):
            missing.append({"name": s.get("name", ""), "freq": s.get("freq", 0), "tier": "bonus"})

    missing.sort(key=lambda x: x["freq"], reverse=True)
    top_missing = missing[:8]

    # Market positioning based on core skill coverage
    core_pct   = core_stats["pct"]
    node_label = node.get("label", "工程师")
    if core_pct >= 80:
        positioning = f"资深{node_label}"
        positioning_level = "senior"
    elif core_pct >= 50:
        positioning = f"中级{node_label}"
        positioning_level = "mid"
    else:
        positioning = f"初级{node_label}"
        positioning_level = "junior"

    return {
        "core":       core_stats,
        "important":  important_stats,
        "bonus":      bonus_stats,
        "top_missing":     top_missing,
        "positioning":     positioning,
        "positioning_level": positioning_level,
    }


# ── Action plan builder ────────────────────────────────────────────────────────

def _build_action_plan(
    gap_skills: list[str],
    node_id: str,
    profile_data: dict,
    current_readiness: float,
) -> dict:
    """Build short (1–3 month) and mid (3–6 month) term action plans."""
    user_skills = _user_skill_set(profile_data)

    # Determine current level bracket from readiness score
    if current_readiness >= 80:
        current_level = 3
    elif current_readiness >= 55:
        current_level = 2
    else:
        current_level = 1

    next_level = current_level + 1
    mid_level = current_level + 2

    # Get per-level skills from level_skills.json (if available)
    level_data = _LEVEL_SKILLS.get(node_id, {})
    levels = level_data.get("levels", {})

    def _level_gaps(level: int) -> list[str]:
        """Skills needed at this level that user doesn't have."""
        lv_info = levels.get(str(level), {})
        lv_skills = lv_info.get("skills", [])
        missing = [s for s in lv_skills if s and not _skill_matches(s, user_skills)]
        return missing[:4]

    short_gaps = _level_gaps(next_level)
    mid_gaps = _level_gaps(mid_level)

    # Fallback to CareerGoal.gap_skills if level_skills not available
    if not short_gaps and gap_skills:
        short_gaps = [s for s in gap_skills[:4] if not _skill_matches(s, user_skills)]
    if not mid_gaps and gap_skills:
        mid_gaps = [s for s in gap_skills[4:8] if not _skill_matches(s, user_skills)]

    def _skill_to_task(skill: str, term: str) -> dict:
        short_map: dict[str, int] = {
            "TypeScript": 30, "React": 25, "Vue": 20, "Python": 35,
            "Docker": 20, "Git": 10, "MySQL": 25, "Redis": 20,
            "Kubernetes": 30, "Linux": 25, "Go": 40, "Rust": 45,
            "JavaScript": 25, "CSS": 15, "HTML": 10,
        }
        hours = next((v for k, v in short_map.items() if k.lower() in skill.lower()), 25)
        return {
            "id": f"{term}_{skill[:8].replace(' ', '_')}",
            "text": f"掌握 {skill}",
            "hours": f"{hours}h",
            "done": False,
        }

    short_tasks = [_skill_to_task(s, "s") for s in short_gaps[:3]]
    mid_tasks = [_skill_to_task(s, "m") for s in mid_gaps[:3]]

    # Add project task if none present in mid term
    if not mid_tasks:
        node_label = _GRAPH_NODES.get(node_id, {}).get("label", "目标岗位")
        mid_tasks.append({
            "id": "m_project",
            "text": f"独立完成一个 {node_label} 方向的实战项目并上线",
            "hours": "60h",
            "done": False,
        })

    # Ensure non-empty short tasks
    if not short_tasks and gap_skills:
        short_tasks = [_skill_to_task(gap_skills[0], "s")]

    return {"short": short_tasks, "mid": mid_tasks}


# ── LLM narrative generator ───────────────────────────────────────────────────

_NARRATIVE_SYSTEM = """你是一位资深职业规划顾问，正在为一名IT学生撰写职业发展报告的核心评估段落。
要求：
- 语言亲切专业，200-300字
- 结合具体数据说话（技能匹配、分数、差距）
- 指出最大亮点和最需改进的1-2个方向
- 结尾给出一句鼓励性总结
- 直接输出段落文字，不要标题或标签"""


def _generate_narrative(
    target_label: str,
    match_score: int,
    four_dim: dict,
    gap_skills: list[str],
    market_info: dict | None,
    growth_delta: float,
) -> str:
    """Call LLM to generate 200-300 char narrative. Falls back to template on error."""
    try:
        from backend.llm import get_llm_client, get_model

        dim_text = []
        dim_labels = {"foundation": "基础要求", "skills": "职业技能",
                      "qualities": "职业素养", "potential": "发展潜力"}
        for k, label in dim_labels.items():
            v = four_dim.get(k)
            dim_text.append(f"- {label}: {v if v is not None else '暂无数据（需完成模拟面试）'}")

        market_text = ""
        if market_info:
            market_text = (
                f"市场信号：该方向需求变化 {market_info.get('demand_change_pct', 0):+.0f}%，"
                f"薪资年增 {market_info.get('salary_cagr', 0):.1f}%，"
                f"入场时机：{market_info.get('timing_label', '良好')}。"
            )

        gap_text = "、".join(gap_skills[:4]) if gap_skills else "暂无明显差距"

        prompt = f"""学生职业发展报告综合评价：

目标岗位：{target_label}
综合匹配分：{match_score}/100
近期成长：readiness score 增长 {growth_delta:+.1f}%

四维评分：
{chr(10).join(dim_text)}

核心技能差距：{gap_text}

{market_text}

请撰写200-300字的综合评价段落，包含：1)当前状态评估 2)最大优势 3)关键改进方向 4)鼓励性收尾。"""

        client = get_llm_client(timeout=30)
        resp = client.chat.completions.create(
            model=get_model("fast"),
            messages=[
                {"role": "system", "content": _NARRATIVE_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=500,
        )
        return resp.choices[0].message.content.strip()

    except Exception as e:
        logger.warning("Narrative generation failed: %s", e)
        # Fallback template
        dim_s = four_dim.get("skills", 0)
        dim_p = four_dim.get("potential", 0)
        return (
            f"你在{target_label}方向的综合匹配度为 {match_score} 分，"
            f"职业技能维度得分 {dim_s}，发展潜力 {dim_p}。"
            f"{'核心差距技能：' + '、'.join(gap_skills[:3]) + '。' if gap_skills else ''}"
            f"建议聚焦提升技术深度，保持当前成长势头，持续积累实战项目经验。"
        )


# ── Main report generator ─────────────────────────────────────────────────────

def generate_report(user_id: int, db) -> dict:
    """
    Generate a complete career development report for the current user.

    Returns the report data dict (to be serialized into Report.data_json).
    Raises ValueError if prerequisite data is missing.
    """
    _load_static()

    from backend.db_models import (
        Profile, CareerGoal, GrowthSnapshot,
        MockInterviewSession, ProjectRecord,
    )

    # 1. Load profile
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        raise ValueError("no_profile")

    profile_data = _parse_profile(profile.profile_json)

    # 2. Load active career goal
    goal = (
        db.query(CareerGoal)
        .filter(
            CareerGoal.user_id == user_id,
            CareerGoal.profile_id == profile.id,
            CareerGoal.is_active == True,
        )
        .order_by(CareerGoal.is_primary.desc(), CareerGoal.set_at.desc())
        .first()
    )
    if not goal:
        raise ValueError("no_goal")

    node_id = goal.target_node_id
    node = _GRAPH_NODES.get(node_id)
    if not node:
        raise ValueError(f"unknown_node:{node_id}")

    # 3. Load growth snapshots (for curve + potential scoring)
    snapshots = (
        db.query(GrowthSnapshot)
        .filter(GrowthSnapshot.profile_id == profile.id)
        .order_by(GrowthSnapshot.created_at.asc())
        .limit(20)
        .all()
    )

    current_readiness = float(snapshots[-1].readiness_score) if snapshots else 0.0
    first_readiness = float(snapshots[0].readiness_score) if snapshots else 0.0
    growth_delta = current_readiness - first_readiness

    growth_curve = [
        {
            "date": s.created_at.strftime("%m/%d") if s.created_at else "",
            "score": round(float(s.readiness_score), 1),
        }
        for s in snapshots
    ]

    # 4. Load mock interview sessions
    mock_sessions = (
        db.query(MockInterviewSession)
        .filter(
            MockInterviewSession.profile_id == profile.id,
            MockInterviewSession.status == "finished",
        )
        .order_by(MockInterviewSession.created_at.desc())
        .limit(5)
        .all()
    )

    # 5. Load projects
    projects = (
        db.query(ProjectRecord)
        .filter(ProjectRecord.user_id == user_id)
        .all()
    )

    # 6. Compute four dimensions
    foundation_score = _score_foundation(profile_data, node)
    skills_score = _score_skills(profile_data, node)
    qualities_score = _score_qualities(mock_sessions)
    potential_score = _score_potential(
        snapshots, projects, float(goal.transition_probability or 0)
    )

    four_dim = {
        "foundation": foundation_score,
        "skills": skills_score,
        "qualities": qualities_score,
        "potential": potential_score,
    }
    match_score = _weighted_match_score(four_dim)

    # 7. Market signals
    family_name = _NODE_TO_FAMILY.get(node_id)
    market_info: dict | None = _MARKET.get(family_name) if family_name else None

    # 8. Build promotion path with per-level gap skills
    promotion_path = []
    level_data = _LEVEL_SKILLS.get(node_id, {})
    levels = level_data.get("levels", {})
    user_skills = _user_skill_set(profile_data)

    raw_pp = node.get("promotion_path") or []
    for pp in raw_pp:
        lv = pp.get("level", 0)
        lv_info = levels.get(str(lv), {})
        lv_skills = lv_info.get("skills", [])
        gap = [s for s in lv_skills if s and not _skill_matches(s, user_skills)][:4]
        # Fallback: if no level_skills, use career_goal gap_skills for level 2 only
        if not gap and lv == 2:
            gap = (goal.gap_skills or [])[:3]

        # Approximate salary ranges from career_ceiling & salary_p50
        salary_p50 = node.get("salary_p50", 0)
        salary_ranges = {
            1: f"{int(salary_p50 * 0.45 / 1000)}k–{int(salary_p50 * 0.7 / 1000)}k",
            2: f"{int(salary_p50 * 0.7 / 1000)}k–{int(salary_p50 * 1.1 / 1000)}k",
            3: f"{int(salary_p50 * 1.1 / 1000)}k–{int(salary_p50 * 1.8 / 1000)}k",
            4: f"{int(salary_p50 * 1.8 / 1000)}k–{int(salary_p50 * 2.9 / 1000)}k",
            5: f"{int(salary_p50 * 2.9 / 1000)}k+",
        }
        exp_ranges = {1: "0–1年", 2: "1–3年", 3: "3–5年", 4: "5–8年", 5: "8年+"}

        promotion_path.append({
            "level": lv,
            "title": pp.get("title", f"Level {lv}"),
            "current": lv == 1 and current_readiness < 40 or (
                lv == 2 and 40 <= current_readiness < 65
            ) or (
                lv == 3 and 65 <= current_readiness < 80
            ) or (
                lv == 4 and 80 <= current_readiness < 92
            ) or (
                lv == 5 and current_readiness >= 92
            ),
            "salary": salary_ranges.get(lv, ""),
            "years": exp_ranges.get(lv, ""),
            "gap_skills": gap,
        })

    # 9. Skill gap analysis (replaces fake promotion_path in frontend)
    skill_gap = _build_skill_gap(profile_data, node)

    # 10. Action plan
    action_plan = _build_action_plan(
        gap_skills=goal.gap_skills or [],
        node_id=node_id,
        profile_data=profile_data,
        current_readiness=current_readiness,
    )

    # 11. LLM narrative
    narrative = _generate_narrative(
        target_label=goal.target_label,
        match_score=match_score,
        four_dim=four_dim,
        gap_skills=goal.gap_skills or [],
        market_info=market_info,
        growth_delta=growth_delta,
    )

    # 12. Assemble report payload
    report_data = {
        "version": "1.0",
        "report_type": "long",
        "student": {
            "user_id": user_id,
            "profile_id": profile.id,
        },
        "target": {
            "node_id": node_id,
            "label": goal.target_label,
            "zone": goal.target_zone,
        },
        "match_score": match_score,
        "four_dim": four_dim,
        "narrative": narrative,
        "market": {
            "demand_change_pct": market_info.get("demand_change_pct", 0) if market_info else None,
            "salary_cagr": market_info.get("salary_cagr", 0) if market_info else None,
            "salary_p50": node.get("salary_p50", 0),
            "timing": market_info.get("timing", "good") if market_info else "good",
            "timing_label": market_info.get("timing_label", "") if market_info else "",
        },
        "promotion_path": promotion_path,
        "skill_gap": skill_gap,
        "growth_curve": growth_curve,
        "action_plan": action_plan,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    return report_data


# ── Polish (AI润色) ────────────────────────────────────────────────────────────

def polish_narrative(narrative: str, target_label: str) -> str:
    """Re-polish an existing narrative via LLM."""
    try:
        from backend.llm import get_llm_client, get_model

        prompt = f"""以下是一段针对「{target_label}」职业方向的发展报告评价段落，请在保留核心信息的前提下进行润色优化：
- 语言更流畅、专业
- 保持200-300字
- 保留所有具体数据
- 结尾保持鼓励性语气

原文：
{narrative}

请直接输出润色后的段落，不需要任何解释。"""

        client = get_llm_client(timeout=30)
        resp = client.chat.completions.create(
            model=get_model("fast"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=600,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("Polish failed: %s", e)
        return narrative
