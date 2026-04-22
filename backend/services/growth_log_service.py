"""成长档案服务 — readiness 估算、面试分析。"""
from __future__ import annotations

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _skill_matches(skill_name: str, user_skills: set[str]) -> bool:
    """Case-insensitive substring match for a skill keyword against user skill set.

    Handles variants like "Spring Boot" vs "SpringBoot", "Redis缓存" vs "Redis".
    Normalization removes spaces/hyphens/underscores before comparison.
    Short keywords (≤2 chars) require exact match to avoid false positives.
    """
    def _norm(s: str) -> str:
        return s.lower().strip().replace(" ", "").replace("-", "").replace("_", "")

    name = skill_name.lower().strip()
    name_norm = _norm(skill_name)
    if not name:
        return False

    # Exact match (raw lowercase)
    if name in user_skills:
        return True

    # Short keyword: only exact match allowed
    if len(name_norm) <= 2:
        return False

    for us in user_skills:
        if not us:
            continue
        us_norm = _norm(us)
        # Normalized exact match (handles SpringBoot vs spring boot)
        if name_norm == us_norm:
            return True
        # Substring match (both directions, normalized)
        if len(us_norm) > 2 and (name_norm in us_norm or us_norm in name_norm):
            return True
    return False


def _compute_readiness_live(profile_id: int, db: Session) -> float | None:
    """Compute readiness from CareerGoal + current skills using real market skill weights.

    Uses skill_tiers (from 48万 JD ETL) with weighted scoring:
      core skills: weight 1.0 (≥50% JD mention rate)
      important:   weight 0.6 (20-49%)
      bonus:       weight 0.3 (5-19%)

    Falls back to flat must_skills matching if skill_tiers unavailable.
    Called after skill updates so the returned value reflects new skills immediately.
    """
    try:
        from backend.models import CareerGoal, Profile
        profile = db.query(Profile).filter(Profile.id == profile_id).first()
        if not profile:
            return None

        goal = (
            db.query(CareerGoal)
            .filter(CareerGoal.profile_id == profile_id, CareerGoal.is_active == True)
            .order_by(CareerGoal.is_primary.desc(), CareerGoal.set_at.desc())
            .first()
        )
        if not goal:
            return None

        from backend.services.graph_service import GraphService
        svc = GraphService()
        svc.load()
        node = svc.get_node(goal.target_node_id)
        if not node:
            return None

        # Build user skill set (lowercase, from both dict-format and string-format)
        profile_data = json.loads(profile.profile_json or "{}")
        raw_skills = profile_data.get("skills", [])
        if raw_skills and isinstance(raw_skills[0], dict):
            user_skills = {s.get("name", "").lower().strip() for s in raw_skills if s.get("name")}
        else:
            user_skills = {s.lower().strip() for s in raw_skills if isinstance(s, str) and s.strip()}

        # ── Tiered scoring (preferred) ──────────────────────────────────────
        tiers = node.get("skill_tiers", {})
        core_list = tiers.get("core", [])
        important_list = tiers.get("important", [])
        bonus_list = tiers.get("bonus", [])

        if core_list or important_list:
            # Weights: core=1.0, important=0.6, bonus=0.3
            total_w = len(core_list) * 1.0 + len(important_list) * 0.6 + len(bonus_list) * 0.3
            if total_w == 0:
                return 0.0
            matched_w = 0.0
            for entry in core_list:
                if _skill_matches(entry["name"], user_skills):
                    matched_w += 1.0
            for entry in important_list:
                if _skill_matches(entry["name"], user_skills):
                    matched_w += 0.6
            for entry in bonus_list:
                if _skill_matches(entry["name"], user_skills):
                    matched_w += 0.3
            return round(min(matched_w / total_w * 100, 100.0), 1)

        # ── Fallback: flat must_skills equal-weight matching ────────────────
        must_skills = [s.lower().strip() for s in node.get("must_skills", []) if s and s.strip()]
        if not must_skills:
            return 0.0
        matched = sum(1 for s in must_skills if _skill_matches(s, user_skills))
        return round(matched / len(must_skills) * 100, 1)

    except Exception as e:
        logger.debug("_compute_readiness_live failed: %s", e)
        return None


def get_current_readiness(profile_id: int, db: Session) -> float | None:
    """获取当前 readiness%。

    优先级：
    1. GrowthSnapshot（最精确，有就用）
    2. CareerGoal gap analysis（用户设定目标后，matched/must_skills 比值）
    3. 实时从图谱计算（兜底，用 profile skills 匹配 top 推荐，上限 80%）
    """
    try:
        from backend.models import GrowthSnapshot, Profile

        # 1. GrowthSnapshot
        snap = (
            db.query(GrowthSnapshot)
            .filter(GrowthSnapshot.profile_id == profile_id)
            .order_by(GrowthSnapshot.created_at.desc())
            .first()
        )
        if snap:
            return float(snap.readiness_score)

        profile = db.query(Profile).filter(Profile.id == profile_id).first()
        if not profile:
            return None

        # 2. CareerGoal gap analysis (most accurate — tied to user's actual target)
        from backend.models import CareerGoal
        goal = (
            db.query(CareerGoal)
            .filter(CareerGoal.profile_id == profile_id, CareerGoal.is_active == True)
            .order_by(CareerGoal.is_primary.desc(), CareerGoal.set_at.desc())
            .first()
        )
        if goal:
            from backend.services.graph_service import GraphService
            svc = GraphService()
            svc.load()
            node = svc.get_node(goal.target_node_id)
            if node:
                must_skills = [s.lower().strip() for s in node.get("must_skills", [])]
                profile_data = json.loads(profile.profile_json or "{}")
                raw_skills = profile_data.get("skills", [])
                if raw_skills and isinstance(raw_skills[0], dict):
                    user_skills = {s.get("name", "").lower().strip() for s in raw_skills}
                else:
                    user_skills = {s.lower().strip() for s in raw_skills if isinstance(s, str)}
                if must_skills:
                    matched = sum(1 for s in must_skills if s in user_skills)
                    return round(matched / len(must_skills) * 100, 1)
                else:
                    return 0.0

        # 3. Live compute from graph using real skill-gap ratio (NOT affinity_pct)
        profile_data = json.loads(profile.profile_json or "{}")
        raw_skills = profile_data.get("skills", [])
        if not raw_skills:
            return None

        if raw_skills and isinstance(raw_skills[0], dict):
            skill_names = [s.get("name", "") for s in raw_skills if s.get("name")]
        else:
            skill_names = [s for s in raw_skills if isinstance(s, str)]

        if not skill_names:
            return None

        from backend.services.graph_service import GraphService
        svc = GraphService()
        svc.load()
        results = svc.recommend_by_skills(skill_names, top_n=1)
        if results:
            top_result = results[0]
            matched_count = top_result.get("overlap_count", 0)
            missing = top_result.get("missing_skills", [])
            total = matched_count + len(missing)
            if total > 0:
                # Cap at 80% without real project/interview evidence
                raw_pct = round(matched_count / total * 100, 1)
                return min(raw_pct, 80.0)

    except Exception as e:
        logger.debug("Could not get readiness: %s", e)
    return None


def generate_interview_analysis(
    *,
    company: str,
    position: str,
    round_: str,
    content_summary: str,
    self_rating: str,
    profile_skills: list[str],
) -> str:
    """用 LLM 生成面试复盘分析，返回 JSON 字符串。"""
    try:
        from backend.llm import get_llm_client, get_model
        client = get_llm_client(timeout=30)
        model = get_model("fast")

        skill_str = ", ".join(profile_skills[:15]) if profile_skills else "未知"
        prompt = f"""你是职业规划教练，帮学生复盘真实面试经历。

面试信息：
- 公司：{company}
- 岗位：{position}
- 轮次：{round_}
- 面试内容：{content_summary}
- 自我评价：{self_rating}（good=发挥好/medium=一般/bad=发挥差）
- 用户技能：{skill_str}

请生成简洁的复盘分析，返回 JSON：
{{
  "strengths": ["做得好的地方（1-2条）"],
  "weaknesses": ["暴露的不足（1-2条）"],
  "action_items": ["下一步建议（1-2条）"],
  "overall": "一句话总结"
}}

直接返回 JSON，不要其他文字。"""

        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=400,
        )
        text = resp.choices[0].message.content.strip()
        # Validate it's parseable
        json.loads(text)
        return text
    except Exception as e:
        logger.warning("Interview analysis generation failed: %s", e)
        return json.dumps({
            "strengths": [],
            "weaknesses": [],
            "action_items": ["继续练习，下次会更好"],
            "overall": "面试经历已记录，保持积累。"
        })



