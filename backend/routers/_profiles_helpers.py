"""Core profile helpers used across profile sub-modules."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from backend.db_models import CareerGoal, JobNode, Profile


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
    from backend.services.graph_service import get_graph_service
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


_LEVEL_ORDER = {"beginner": 0, "familiar": 1, "intermediate": 2, "advanced": 3}


def _merge_profiles(existing: dict, incoming: dict) -> dict:
    """Merge incoming profile data into existing.

    - Skills: union, keep higher level for duplicates.
    - knowledge_areas / projects / awards: set union.
    - education / experience_years: update if incoming has richer data.
    - raw_text: always overwrite with latest upload.
    - soft_skills: preserve existing assessment unless incoming has one.
    """
    merged = dict(existing)

    # Skills: union, higher level wins
    skill_map = {s["name"]: s for s in existing.get("skills", [])}
    for skill in incoming.get("skills", []):
        name = skill["name"]
        if name not in skill_map:
            skill_map[name] = skill
        else:
            existing_lvl = _LEVEL_ORDER.get(skill_map[name].get("level", "beginner"), 0)
            incoming_lvl = _LEVEL_ORDER.get(skill.get("level", "beginner"), 0)
            if incoming_lvl > existing_lvl:
                skill_map[name] = skill
    merged["skills"] = list(skill_map.values())

    # knowledge_areas / projects / awards: union
    merged["knowledge_areas"] = list(
        set(existing.get("knowledge_areas", [])) | set(incoming.get("knowledge_areas", []))
    )
    merged["projects"] = list(
        set(existing.get("projects", [])) | set(incoming.get("projects", []))
    )
    merged["awards"] = list(
        set(existing.get("awards", [])) | set(incoming.get("awards", []))
    )

    # certificates: union by name (case-insensitive dedup)
    existing_certs = {c.lower(): c for c in existing.get("certificates", [])}
    for cert in incoming.get("certificates", []):
        existing_certs.setdefault(cert.lower(), cert)
    merged["certificates"] = list(existing_certs.values())

    # internships: union by (company + role), keep most recent if duplicate
    existing_interns = {
        (i.get("company", "") + "|" + i.get("role", "")): i
        for i in existing.get("internships", [])
        if isinstance(i, dict)
    }
    for intern in incoming.get("internships", []):
        if not isinstance(intern, dict):
            continue
        key = intern.get("company", "") + "|" + intern.get("role", "")
        existing_interns[key] = intern  # incoming overwrites (more recent upload = fresher data)
    merged["internships"] = list(existing_interns.values())

    # Education: update if incoming has richer data
    if incoming.get("education") and any(v for v in incoming["education"].values() if v):
        merged["education"] = incoming["education"]

    # experience_years: keep max (safe against None values stored in existing data)
    inc_exp = incoming.get("experience_years") or 0
    exs_exp = existing.get("experience_years") or 0
    merged["experience_years"] = max(inc_exp, exs_exp)

    # name: update if incoming provides one
    if incoming.get("name"):
        merged["name"] = incoming["name"]

    # raw_text: always use latest
    if incoming.get("raw_text"):
        merged["raw_text"] = incoming["raw_text"]

    # soft_skills: preserve existing assessment; only set if currently absent
    if not merged.get("soft_skills") and incoming.get("soft_skills"):
        merged["soft_skills"] = incoming["soft_skills"]

    # job_target: incoming wins if non-empty, else keep existing
    if incoming.get("job_target"):
        merged["job_target"] = incoming["job_target"]
    elif existing.get("job_target"):
        merged["job_target"] = existing["job_target"]  # preserve, never overwrite with empty

    # primary_domain: incoming wins if non-empty, else keep existing
    if incoming.get("primary_domain"):
        merged["primary_domain"] = incoming["primary_domain"]
    elif existing.get("primary_domain"):
        merged["primary_domain"] = existing["primary_domain"]

    return merged


def _execute_profile_reset(user_id: int, profile: Profile, db: Session) -> None:
    """Wipe all profile-derived artifacts for the given user."""
    from backend.db_models import (
        CareerGoal,
        CoachResult,
        InterviewDebrief,
        InterviewRecord,
        JDDiagnosis,
        JobApplication,
        ProjectLog,
        ProjectRecord,
        Report,
        SjtSession,
    )

    profile.profile_json = "{}"
    profile.quality_json = "{}"
    profile.name = ""
    profile.source = "manual"

    # Children first (FK dependencies): project_logs → project_records,
    # interview_records → job_applications (via application_id).
    project_ids = [
        pid for (pid,) in db.query(ProjectRecord.id)
        .filter(ProjectRecord.user_id == user_id)
        .all()
    ]
    if project_ids:
        db.query(ProjectLog).filter(
            ProjectLog.project_id.in_(project_ids)
        ).delete(synchronize_session=False)

    db.query(InterviewRecord).filter(
        InterviewRecord.user_id == user_id
    ).delete(synchronize_session=False)

    db.query(InterviewDebrief).filter(
        InterviewDebrief.user_id == user_id
    ).delete(synchronize_session=False)

    db.query(JobApplication).filter(
        JobApplication.user_id == user_id
    ).delete(synchronize_session=False)

    db.query(ProjectRecord).filter(
        ProjectRecord.user_id == user_id
    ).delete(synchronize_session=False)

    # Report history + JD diagnostic runs + coach results all bake in
    # the old profile snapshot. Fresh upload must produce fresh reports.
    db.query(Report).filter(
        Report.user_id == user_id
    ).delete(synchronize_session=False)

    db.query(JDDiagnosis).filter(
        JDDiagnosis.user_id == user_id
    ).delete(synchronize_session=False)

    db.query(CoachResult).filter(
        CoachResult.user_id == user_id
    ).delete(synchronize_session=False)

    # SJT is profile-scoped (no user_id column); filter by the profile.id.
    db.query(SjtSession).filter(
        SjtSession.profile_id == profile.id
    ).delete(synchronize_session=False)

    # Single-profile system: delete all career goals by user_id.
    db.query(CareerGoal).filter(
        CareerGoal.user_id == user_id
    ).delete(synchronize_session=False)

    # Safety net: warn if new FK-linked tables appear but aren't in explicit list
    try:
        from sqlalchemy import inspect as sa_inspect
        from backend.db import Base

        def _enumerate_user_owned_tables(metadata):
            tables = []
            for table_name, table in metadata.tables.items():
                for col in table.columns:
                    for fk in col.foreign_keys:
                        if fk.column.table.name in ("users", "profiles"):
                            tables.append((table_name, col.name))
                            break
            return tables

        _auto = _enumerate_user_owned_tables(Base.metadata)
        _known = {
            "project_logs", "interview_records", "interview_debriefs",
            "job_applications", "project_records", "reports", "jd_diagnoses",
            "coach_results", "sjt_sessions", "career_goals",
        }
        _missing = [t for t, _ in _auto if t not in _known]
        if _missing:
            import logging
            logging.getLogger(__name__).warning(
                "reset_profile: tables FK-linked to user/profile but NOT in explicit list: %s",
                _missing,
            )
    except Exception:
        pass

    db.commit()
