"""Profile merge and reset helpers."""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from backend.models import CareerGoal

if TYPE_CHECKING:
    from backend.models import Profile

logger = logging.getLogger(__name__)

_LEVEL_ORDER = {"beginner": 0, "familiar": 1, "intermediate": 2, "advanced": 3}


def merge_skills(sdk_skills: list[dict], llm_skills: list[dict]) -> list[dict]:
    """Merge two skill lists: SDK (coarse but reliable) + LLM (granular but may hallucinate).

    Rules:
    1. Union by name (case-insensitive).
    2. Higher level wins.
    3. If same level, prefer LLM's entry (more granular / context-aware).
    4. LLM skills that are sub-skills of SDK skills are kept (e.g. SDK: C++ → LLM: epoll).
    """
    skill_map: dict[str, dict] = {}

    for s in sdk_skills:
        name = s.get("name", "").strip()
        if name:
            skill_map[name.lower()] = {"name": name, "level": s.get("level", "familiar")}

    for s in llm_skills:
        name = s.get("name", "").strip()
        if not name:
            continue
        key = name.lower()
        llm_level = _LEVEL_ORDER.get(s.get("level", "beginner"), 0)

        if key not in skill_map:
            skill_map[key] = {"name": name, "level": s.get("level", "familiar")}
        else:
            existing_level = _LEVEL_ORDER.get(skill_map[key].get("level", "beginner"), 0)
            if llm_level > existing_level:
                skill_map[key] = {"name": name, "level": s.get("level", "familiar")}
            elif llm_level == existing_level:
                skill_map[key] = {"name": name, "level": s.get("level", "familiar")}

    return list(skill_map.values())


def merge_profiles(existing: dict, incoming: dict) -> dict:
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
        existing_interns[key] = intern
    merged["internships"] = list(existing_interns.values())

    # Education: update if incoming has richer data
    if incoming.get("education") and any(v for v in incoming["education"].values() if v):
        merged["education"] = incoming["education"]

    # experience_years: keep max
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
        merged["job_target"] = existing["job_target"]

    # primary_domain: incoming wins if non-empty, else keep existing
    if incoming.get("primary_domain"):
        merged["primary_domain"] = incoming["primary_domain"]
    elif existing.get("primary_domain"):
        merged["primary_domain"] = existing["primary_domain"]

    return merged


def execute_profile_reset(user_id: int, profile: "Profile", db: Session) -> None:
    """Wipe all profile-derived artifacts for the given user."""
    from backend.models import (
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

    # Children first (FK dependencies)
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
            logging.getLogger(__name__).warning(
                "reset_profile: tables FK-linked to user/profile but NOT in explicit list: %s",
                _missing,
            )
    except Exception:
        pass

    db.commit()
