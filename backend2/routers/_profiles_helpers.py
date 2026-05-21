"""Core profile helpers used across profile sub-modules."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from backend.models import CareerGoal, JobNode, Profile
from backend.services.profile.merge import (
    merge_profiles,
    merge_skills,
    execute_profile_reset,
)


def _get_or_create_profile(user_id: int, db: Session) -> Profile:
    """Return the user's single profile, creating an empty one if none exists."""
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        profile = Profile(
            user_id=user_id,
            name="",
            profile_json="{}",
            quality_json="{}",
            source="manual",
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def _resolve_node_label(node_id: str, db: Session) -> str:
    """Resolve node label: try graph service first, then DB, then raw ID."""
    from backend.services.graph import get_graph_service
    g = get_graph_service(db)
    gn = g.get_node(node_id)
    if gn:
        return gn.get("label", node_id)
    db_node = db.query(JobNode).filter(JobNode.node_id == node_id).first()
    return db_node.label if db_node else node_id


def _profile_to_dict(profile: Profile, db: Session, user_id: int) -> dict:
    """Serialize a profile with its graph position."""
    # 获取所有 active goals，is_primary 优先
    all_goals = (
        db.query(CareerGoal)
        .filter(
            CareerGoal.user_id == user_id,
            CareerGoal.profile_id == profile.id,
            CareerGoal.is_active == True,
        )
        .order_by(CareerGoal.is_primary.desc(), CareerGoal.set_at.desc())
        .all()
    )
    primary_goal = next((g for g in all_goals if g.is_primary), all_goals[0] if all_goals else None)

    profile_data = json.loads(profile.profile_json or "{}")
    item: dict = {
        "id": profile.id,
        "name": profile.name,
        "source": profile.source,
        "created_at": str(profile.created_at),
        "updated_at": str(profile.updated_at),
        "profile": profile_data,
        "quality": json.loads(profile.quality_json or "{}"),
    }

    # graph_position: 向后兼容，取主目标快照
    if primary_goal and (primary_goal.from_node_id or primary_goal.target_node_id):
        item["graph_position"] = {
            "from_node_id": primary_goal.from_node_id,
            "from_node_label": _resolve_node_label(primary_goal.from_node_id, db),
            "target_node_id": primary_goal.target_node_id,
            "target_label": primary_goal.target_label,
            "target_zone": primary_goal.target_zone,
            "gap_skills": primary_goal.gap_skills or [],
            "total_hours": primary_goal.total_hours or 0,
            "safety_gain": primary_goal.safety_gain or 0.0,
            "salary_p50": primary_goal.salary_p50 or 0,
        }

    # career_goals: 完整多目标列表 — 只要有 active goal 且有 target 就返回
    goals_with_target = [g for g in all_goals if g.target_node_id]
    if goals_with_target:
        # from_node_id may be empty (e.g. set from role detail page before auto_locate)
        from_node_id = goals_with_target[0].from_node_id or ""
        from_node_label = _resolve_node_label(from_node_id, db) if from_node_id else ""

        item["career_goals"] = [
            {
                "id": g.id,
                "target_node_id": g.target_node_id,
                "target_label": g.target_label,
                "target_zone": g.target_zone,
                "from_node_id": g.from_node_id or from_node_id,
                "from_node_label": from_node_label,
                "gap_skills": g.gap_skills or [],
                "total_hours": g.total_hours or 0,
                "safety_gain": g.safety_gain or 0.0,
                "salary_p50": g.salary_p50 or 0,
                "is_primary": g.is_primary,
                "set_at": g.set_at.isoformat() if g.set_at else None,
            }
            for g in goals_with_target
        ]
    else:
        item["career_goals"] = []

    return item


def _load_profile_json(profile: Profile) -> dict:
    return json.loads(profile.profile_json or "{}")


# Re-export for backward compatibility
_merge_skills = merge_skills
_merge_profiles = merge_profiles
_execute_profile_reset = execute_profile_reset
