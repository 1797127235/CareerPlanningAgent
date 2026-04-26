"""Growth dashboard data aggregation."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from backend.models import CareerGoal, GrowthSnapshot, Profile
from backend.services.graph import GraphService
from backend.services._shared.skill_match import skill_matches as _skill_matches

if TYPE_CHECKING:
    from backend.models import User

logger = logging.getLogger(__name__)


def build_growth_dashboard(user: "User", db: Session) -> dict:
    """获取成长看板数据：目标方向 + 分层技能覆盖率 + 匹配度曲线。"""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        return {"has_goal": False, "has_profile": False}

    goal = (
        db.query(CareerGoal)
        .filter(
            CareerGoal.user_id == user.id,
            CareerGoal.profile_id == profile.id,
            CareerGoal.is_active == True,
        )
        .order_by(CareerGoal.is_primary.desc(), CareerGoal.set_at.desc())
        .first()
    )

    if not goal or not goal.target_node_id:
        return {"has_goal": False, "has_profile": True}

    svc = GraphService()
    svc.load()
    node = svc.get_node(goal.target_node_id)
    if not node:
        return {"has_goal": False, "has_profile": True}

    # Build user skill set
    try:
        profile_data = json.loads(profile.profile_json or "{}")
    except Exception:
        profile_data = {}
    raw_skills = profile_data.get("skills", [])
    if raw_skills and isinstance(raw_skills[0], dict):
        user_skills = {
            s.get("name", "").lower().strip() for s in raw_skills if s.get("name")
        }
    else:
        user_skills = {
            s.lower().strip() for s in raw_skills if isinstance(s, str) and s.strip()
        }

    # Tiered skill coverage
    tiers = node.get("skill_tiers", {}) or {}
    core_list = tiers.get("core", []) or []
    imp_list = tiers.get("important", []) or []
    bonus_list = tiers.get("bonus", []) or []

    def _count_matched(skills_list):
        matched_items = [
            s for s in skills_list if _skill_matches(s.get("name", ""), user_skills)
        ]
        return len(matched_items), [s.get("name") for s in matched_items]

    core_cnt, core_matched = _count_matched(core_list)
    imp_cnt, imp_matched = _count_matched(imp_list)
    bonus_cnt, bonus_matched = _count_matched(bonus_list)

    def _pct(cnt: int, total: int) -> int:
        return int(round(cnt / total * 100)) if total > 0 else 0

    core_missing = [
        s.get("name")
        for s in core_list
        if not _skill_matches(s.get("name", ""), user_skills)
    ]
    imp_missing = [
        s.get("name")
        for s in imp_list
        if not _skill_matches(s.get("name", ""), user_skills)
    ]

    # Readiness curve from GrowthSnapshot (up to last 12 points)
    snapshots = (
        db.query(GrowthSnapshot)
        .filter(GrowthSnapshot.profile_id == profile.id)
        .order_by(GrowthSnapshot.created_at.asc())
        .limit(12)
        .all()
    )
    curve = [
        {
            "date": s.created_at.strftime("%m/%d") if s.created_at else "",
            "score": round(s.readiness_score or 0, 1),
        }
        for s in snapshots
    ]

    start_date = profile.created_at
    days_since_start = (
        (datetime.now(timezone.utc) - start_date.replace(tzinfo=timezone.utc)).days
        if start_date
        else 0
    )

    return {
        "has_goal": True,
        "has_profile": True,
        "goal": {
            "target_node_id": goal.target_node_id,
            "target_label": goal.target_label,
        },
        "days_since_start": days_since_start,
        "skill_coverage": {
            "core": {
                "covered": core_cnt,
                "total": len(core_list),
                "pct": _pct(core_cnt, len(core_list)),
                "matched": core_matched,
                "missing": core_missing,
            },
            "important": {
                "covered": imp_cnt,
                "total": len(imp_list),
                "pct": _pct(imp_cnt, len(imp_list)),
                "matched": imp_matched,
                "missing": imp_missing,
            },
            "bonus": {
                "covered": bonus_cnt,
                "total": len(bonus_list),
                "pct": _pct(bonus_cnt, len(bonus_list)),
            },
        },
        "gap_skills": goal.gap_skills or [],
        "readiness_curve": curve,
    }
