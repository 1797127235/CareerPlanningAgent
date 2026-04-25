"""Guidance router — AI-driven contextual next-step recommendations.

The guidance engine computes the user's journey stage from DB state
and returns a page-aware recommendation with CTA.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.auth import get_current_user
from backend.db import get_db
from backend.models import (
    InterviewRecord,
    JDDiagnosis,
    JobApplication,
    Profile,
    ProjectRecord,
    Report,
    User,
    UserNotification,
)

logger = logging.getLogger(__name__)

from backend.services.growth.stage import compute_stage

router = APIRouter()


# ── Guidance rules per (stage × page) ────────────────────────────────────────

def _build_guidance(
    stage: str,
    page: str,
    profile_name: str,
    jd_count: int,
    activity_count: int,
    latest_match_score: int | None,
    competitiveness: int,
    app_count: int = 0,
    has_applied: bool = False,
    has_scheduled: bool = False,
) -> dict:
    """Return {message, cta_text, cta_route, tone} based on stage + current page."""

    # Default fallback
    result = {
        "stage": stage,
        "message": "",
        "cta_text": "",
        "cta_route": "",
        "tone": "neutral",  # neutral | encouraging | celebrating | urgent
    }

    if stage == "no_profile":
        result["message"] = "你好！我是你的职业规划顾问。第一步：建立你的能力画像，上传简历或手动填写都可以。"
        result["cta_text"] = "建立画像"
        result["cta_route"] = "/profile"
        result["tone"] = "encouraging"
        return result

    if stage == "has_profile":
        if page == "profile":
            result["message"] = f"画像已就位！竞争力 {competitiveness} 分。把一份真实 JD 粘到右侧教练，我来帮你诊断匹配度。"
            result["cta_text"] = ""
            result["cta_route"] = ""
            result["tone"] = "encouraging"
        else:
            result["message"] = f"{profile_name}，你的画像已建好。把一份真实 JD 粘到右侧教练，我来帮你诊断匹配度。"
            result["cta_text"] = ""
            result["cta_route"] = ""
            result["tone"] = "encouraging"
        return result

    if stage == "first_diagnosis":
        score_text = f"上次匹配度 {latest_match_score}%，" if latest_match_score else ""
        if page == "jd":
            result["message"] = f"{score_text}发现了技能缺口？把它作为目标追踪，从项目实战补齐。"
            result["cta_text"] = "去成长档案"
            result["cta_route"] = "/growth-log"
            result["tone"] = "encouraging"
        elif has_scheduled:
            result["message"] = f"{score_text}已有面试安排，保持状态，查看你的投递进度。"
            result["cta_text"] = "查看投递"
            result["cta_route"] = "/growth-log?tab=pursuits"
            result["tone"] = "encouraging"
        elif has_applied:
            result["message"] = f"{score_text}你已投递 {app_count} 个岗位，继续记录进展。"
            result["cta_text"] = "查看投递"
            result["cta_route"] = "/growth-log?tab=pursuits"
            result["tone"] = "encouraging"
        else:
            result["message"] = f"{score_text}接下来可以记录投递，用项目补齐缺口技能。"
            result["cta_text"] = "去成长档案"
            result["cta_route"] = "/growth-log"
            result["tone"] = "encouraging"
        return result

    if stage == "training":
        if page == "growth":
            result["message"] = f"已有 {activity_count} 次成长记录。继续积累项目与投递，数据越完整，报告越有价值。"
            result["cta_text"] = ""
            result["cta_route"] = ""
            result["tone"] = "celebrating"
        else:
            result["message"] = f"已做了 {jd_count} 次诊断。去成长档案看看你的进步。"
            result["cta_text"] = "查看成长档案"
            result["cta_route"] = "/growth-log"
            result["tone"] = "encouraging"
        return result

    if stage == "growing":
        if page == "growth":
            result["message"] = "成长档案越来越丰富了！可以生成一份完整的职业发展报告，记录你的轨迹。"
            result["cta_text"] = "生成发展报告"
            result["cta_route"] = "/report"
            result["tone"] = "celebrating"
        elif page == "report":
            result["message"] = "数据已就绪，点击「生成新报告」，AI 会基于你的全部数据撰写个性化职业发展报告。"
            result["cta_text"] = ""
            result["cta_route"] = ""
            result["tone"] = "neutral"
        else:
            result["message"] = f"你已经积累了 {jd_count} 次诊断、{activity_count} 条成长记录。该出一份报告了！"
            result["cta_text"] = "生成发展报告"
            result["cta_route"] = "/report"
            result["tone"] = "celebrating"
        return result

    # report_ready — full cycle complete
    if page == "report":
        result["message"] = "报告已生成。继续粘 JD 到右侧教练或补齐档案，报告会随之更新。"
        result["cta_text"] = ""
        result["cta_route"] = ""
        result["tone"] = "neutral"
    else:
        result["message"] = "你的职业规划闭环已完成！保持记录节奏，定期更新画像和报告。"
        result["cta_text"] = "查看发展报告"
        result["cta_route"] = "/report"
        result["tone"] = "celebrating"

    return result


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.get("")
@router.get("/")
def get_guidance(
    page: str = Query("home", description="当前页面: home|profile|graph|jd|practice|growth|report"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return contextual next-step guidance based on user journey stage."""

    # Aggregate user state from DB
    profile_count = db.query(func.count(Profile.id)).filter_by(user_id=user.id).scalar() or 0
    jd_count = db.query(func.count(JDDiagnosis.id)).filter_by(user_id=user.id).scalar() or 0

    # activity_count = 项目 + 实战 + 面试记录
    project_count = db.query(func.count(ProjectRecord.id)).filter_by(user_id=user.id).scalar() or 0
    app_count = db.query(func.count(JobApplication.id)).filter_by(user_id=user.id).scalar() or 0
    interview_count = db.query(func.count(InterviewRecord.id)).filter_by(user_id=user.id).scalar() or 0
    activity_count = project_count + app_count + interview_count

    report_count = db.query(func.count(Report.id)).filter_by(user_id=user.id).scalar() or 0

    stage = compute_stage(profile_count, jd_count, activity_count, report_count)

    # Get profile name + competitiveness
    profile_name = "同学"
    competitiveness = 0
    latest_profile = (
        db.query(Profile)
        .filter_by(user_id=user.id)
        .order_by(Profile.updated_at.desc())
        .first()
    )
    if latest_profile:
        profile_name = latest_profile.name or "同学"
        quality = json.loads(latest_profile.quality_json or "{}")
        comp = quality.get("competitiveness", 0)
        competitiveness = round(comp * 100) if comp <= 1 else round(comp)

    # Latest JD match score
    latest_match_score = None
    if jd_count > 0:
        latest_jd = (
            db.query(JDDiagnosis)
            .filter_by(user_id=user.id)
            .order_by(JDDiagnosis.created_at.desc())
            .first()
        )
        if latest_jd:
            latest_match_score = latest_jd.match_score

    # JobApplication state — read-only aggregates, no business logic
    from datetime import datetime, timedelta, timezone as tz
    now = datetime.now(tz.utc)
    active_app_count = db.query(func.count(JobApplication.id)).filter(
        JobApplication.user_id == user.id,
        JobApplication.status != "pending",
    ).scalar() or 0
    has_applied = active_app_count > 0 and db.query(JobApplication).filter(
        JobApplication.user_id == user.id,
        JobApplication.status.in_(["applied", "screening"]),
    ).first() is not None
    has_scheduled = db.query(JobApplication).filter(
        JobApplication.user_id == user.id,
        JobApplication.status == "scheduled",
        JobApplication.interview_at.isnot(None),
        JobApplication.interview_at > now,
    ).first() is not None

    guidance = _build_guidance(
        stage=stage,
        page=page,
        profile_name=profile_name,
        jd_count=jd_count,
        activity_count=activity_count,
        latest_match_score=latest_match_score,
        competitiveness=competitiveness,
        app_count=active_app_count,
        has_applied=has_applied,
        has_scheduled=has_scheduled,
    )

    # Priority override: upcoming interview reminder (within 24h)
    upcoming = (
        db.query(JobApplication)
        .filter(
            JobApplication.user_id == user.id,
            JobApplication.status == "scheduled",
            JobApplication.interview_at.isnot(None),
            JobApplication.interview_at <= now + timedelta(hours=24),
            JobApplication.interview_at >= now,
        )
        .order_by(JobApplication.interview_at.asc())
        .first()
    )
    if upcoming:
        label = upcoming.position or upcoming.company or "面试"
        dt = upcoming.interview_at
        time_str = dt.strftime("%m/%d %H:%M") if dt else ""
        guidance["message"] = f"提醒：{label} 面试即将到来（{time_str}），记得提前准备！"
        guidance["cta_text"] = "查看投递详情"
        guidance["cta_route"] = "/growth-log?tab=pursuits"
        guidance["tone"] = "urgent"

    # Surface: interviewed status with actual InterviewRecord but no AI analysis yet
    elif db.query(JobApplication).filter(
        JobApplication.user_id == user.id,
        JobApplication.status == "interviewed",
        JobApplication.company.isnot(None),
    ).join(
        InterviewRecord,
        InterviewRecord.application_id == JobApplication.id,
        isouter=False,
    ).filter(
        InterviewRecord.ai_analysis.is_(None),
        InterviewRecord.content_summary.isnot(None),
        InterviewRecord.content_summary != "",
    ).first():
        guidance["message"] = "你有一轮面试还没 AI 复盘，趁记忆新鲜分析一下。"
        guidance["cta_text"] = "去复盘"
        guidance["cta_route"] = "/growth-log?tab=pursuits"
        guidance["tone"] = "urgent"

    return guidance


# ── Coach intervention helpers (used by other routers) ───────────────────────

def create_coach_intervention(
    db: Session,
    user_id: int,
    trigger_type: str,
    title: str,
    body: str,
    cta_label: str = "",
    cta_route: str = "",
    ttl_hours: int = 168,
) -> bool:
    """Create a coach intervention notification if the user hasn't received
    the same trigger_type within the TTL window (default 7 days).
    Returns True if created, False if skipped (dedup).
    """
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(hours=ttl_hours)
    dup = (
        db.query(UserNotification)
        .filter(
            UserNotification.user_id == user_id,
            UserNotification.trigger_type == trigger_type,
            UserNotification.created_at >= cutoff,
        )
        .first()
    )
    if dup:
        logger.info("[CoachIntervention] skipped: dup found for user=%s trigger=%s", user_id, trigger_type)
        return False

    note = UserNotification(
        user_id=user_id,
        kind="coach_intervention",
        trigger_type=trigger_type,
        title=title,
        body=body,
        cta_label=cta_label or None,
        cta_route=cta_route or None,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=ttl_hours) if ttl_hours else None,
    )
    db.add(note)
    db.commit()
    logger.info("[CoachIntervention] created: user=%s trigger=%s id=%s", user_id, trigger_type, note.id)
    return True
