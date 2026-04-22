"""Hydrate CareerState from user DB data for chat sessions."""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from backend.models import (
    ActionPlanV2,
    ActionProgress,
    CareerGoal,
    JDDiagnosis,
    JobApplication,
    Profile,
    ProjectRecord,
)
from backend.services.growth.stage import determine_stage

if TYPE_CHECKING:
    from backend.models import User

logger = logging.getLogger(__name__)


def hydrate_state(user: "User", db: Session) -> dict:
    """Build a rich initial CareerState from the user's DB data."""
    state: dict = {
        "user_id": user.id,
        "profile_id": None,
        "user_profile": None,
        "career_goal": None,
        "current_node_id": None,
        "user_stage": "no_profile",
        "last_diagnosis": None,
    }

    # 1. Active profile
    profile = (
        db.query(Profile)
        .filter_by(user_id=user.id)
        .order_by(Profile.updated_at.desc())
        .first()
    )
    if profile:
        state["profile_id"] = profile.id
        try:
            state["user_profile"] = json.loads(profile.profile_json or "{}")
        except (json.JSONDecodeError, TypeError):
            state["user_profile"] = {}

    # 2. Career goal — exclude placeholder goals (target_node_id="")
    goal = (
        db.query(CareerGoal)
        .filter(
            CareerGoal.user_id == user.id,
            CareerGoal.is_active == True,  # noqa: E712
            CareerGoal.target_node_id != "",
        )
        .order_by(CareerGoal.set_at.desc())
        .first()
    )
    if goal:
        state["career_goal"] = {
            "label": goal.target_label,
            "node_id": goal.target_node_id,
            "zone": goal.target_zone,
        }
        state["current_node_id"] = goal.target_node_id

    # 3. Latest JD diagnosis
    latest_jd = (
        db.query(JDDiagnosis)
        .filter_by(user_id=user.id)
        .order_by(JDDiagnosis.created_at.desc())
        .first()
    )
    if latest_jd:
        try:
            result = json.loads(latest_jd.result_json or "{}")
            state["last_diagnosis"] = {
                "match_score": latest_jd.match_score,
                "jd_title": latest_jd.jd_title,
                "gap_skills": result.get("gap_skills", []),
            }
        except (json.JSONDecodeError, TypeError):
            pass

    # 4. Compute journey stage (新 4 阶段)
    state["user_stage"] = determine_stage(user.id, db)

    # 4b. Inject cached recommendations for coach context + tools
    state["recommended_labels"] = []
    state["recommended_data"] = []
    if profile:
        db.refresh(profile)
        try:
            cached = json.loads(profile.cached_recs_json or "{}")
            recs = cached.get("data", {}).get("recommendations", [])
            state["recommended_data"] = recs
            state["recommended_labels"] = [
                r.get("label") or r.get("role_id", "")
                for r in recs if r.get("label") or r.get("role_id")
            ]
        except (json.JSONDecodeError, TypeError):
            pass

    # 5. Growth coach state
    state["coach_memo"] = ""
    state["page_context"] = None
    state["tool_hint"] = ""
    state["last_active_agent"] = ""
    if profile:
        state["coach_memo"] = profile.coach_memo or ""

    # 6. Growth log context — lightweight metadata only (details via tools)
    try:
        projects = (
            db.query(ProjectRecord)
            .filter_by(user_id=user.id)
            .order_by(ProjectRecord.created_at.desc())
            .limit(5)
            .all()
        )
        pursuits = (
            db.query(JobApplication)
            .filter(
                JobApplication.user_id == user.id,
                ~JobApplication.status.in_(["withdrawn", "rejected"]),
            )
            .order_by(JobApplication.created_at.desc())
            .limit(5)
            .all()
        )
        state["growth_context"] = {
            "projects": [
                {
                    "name": p.name,
                    "status": p.status,
                    "skills": (p.skills_used or [])[:5],
                    "description": (p.description or "")[:80],
                }
                for p in projects
            ],
            "pursuits": [
                {
                    "company": a.company or "",
                    "position": a.position or "",
                    "status": a.status,
                }
                for a in pursuits
            ],
        }
    except Exception:
        logger.exception("Failed to load growth context")
        state["growth_context"] = None

    # 7. Action plan context — current stage tasks from ActionPlanV2
    state["action_plan_context"] = None
    if profile:
        try:
            latest_plan = (
                db.query(ActionPlanV2)
                .filter(ActionPlanV2.profile_id == profile.id)
                .order_by(ActionPlanV2.generated_at.desc())
                .first()
            )
            if latest_plan:
                report_key = latest_plan.report_key
                stages = (
                    db.query(ActionPlanV2)
                    .filter(ActionPlanV2.profile_id == profile.id, ActionPlanV2.report_key == report_key)
                    .order_by(ActionPlanV2.stage)
                    .all()
                )
                progress = (
                    db.query(ActionProgress)
                    .filter(ActionProgress.profile_id == profile.id, ActionProgress.report_key == report_key)
                    .first()
                )
                checked = progress.checked if progress else {}
                plan_stages = []
                for s in stages:
                    content = s.content if isinstance(s.content, dict) else json.loads(s.content or "{}")
                    items = content.get("items", [])
                    total = len(items)
                    done = sum(1 for it in items if checked.get(it.get("id", "")))
                    pending = [it.get("text", "")[:40] for it in items if not checked.get(it.get("id", ""))]
                    plan_stages.append({
                        "stage": content.get("stage", s.stage),
                        "label": content.get("label", ""),
                        "total": total,
                        "done": done,
                        "pending_preview": pending[:2],
                    })
                state["action_plan_context"] = {"stages": plan_stages}
        except Exception:
            logger.debug("Failed to load action plan context", exc_info=True)

    return state
