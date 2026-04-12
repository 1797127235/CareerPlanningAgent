"""Guidance router — AI-driven contextual next-step recommendations.

The guidance engine computes the user's journey stage from DB state
and returns a page-aware recommendation with CTA.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.auth import get_current_user
from backend.db import get_db
from backend.db_models import (
    InterviewRecord,
    InterviewReview,
    JDDiagnosis,
    JobApplication,
    Profile,
    Report,
    User,
)

logger = logging.getLogger(__name__)

from backend.services.stage import compute_stage

router = APIRouter()


# ── Guidance rules per (stage × page) ────────────────────────────────────────

def _build_guidance(
    stage: str,
    page: str,
    profile_name: str,
    jd_count: int,
    review_count: int,
    latest_match_score: int | None,
    latest_review_score: int | None,
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
            result["message"] = f"画像已就位！竞争力 {competitiveness} 分。下一步：找一份感兴趣的岗位 JD，测测匹配度。"
            result["cta_text"] = "去做 JD 诊断"
            result["cta_route"] = "/jd"
            result["tone"] = "encouraging"
        elif page == "jd":
            result["message"] = "粘贴一份真实 JD，AI 会从四个维度分析你和这个岗位的匹配度。"
            result["cta_text"] = ""
            result["cta_route"] = ""
            result["tone"] = "neutral"
        else:
            result["message"] = f"{profile_name}，你的画像已建好。用一份真实 JD 来测测自己的匹配度？"
            result["cta_text"] = "去做 JD 诊断"
            result["cta_route"] = "/jd"
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
        score_text = f"面试平均分 {latest_review_score}，" if latest_review_score else ""
        if page == "growth":
            result["message"] = f"{score_text}已有 {review_count} 次活动记录。继续积累，数据越多成长曲线越清晰。"
            result["cta_text"] = ""
            result["cta_route"] = ""
            result["tone"] = "celebrating"
        else:
            result["message"] = f"{score_text}已做了 {jd_count} 次诊断。去成长档案看看你的进步。"
            result["cta_text"] = "查看成长档案"
            result["cta_route"] = "/growth-log"
            result["tone"] = "encouraging"
        return result

    if stage == "growing":
        if page == "growth":
            result["message"] = "训练数据丰富了！可以生成一份完整的职业发展报告，记录你的成长轨迹。"
            result["cta_text"] = "生成发展报告"
            result["cta_route"] = "/report"
            result["tone"] = "celebrating"
        elif page == "report":
            result["message"] = "数据已就绪，点击「生成新报告」，AI 会基于你的全部数据撰写个性化职业发展报告。"
            result["cta_text"] = ""
            result["cta_route"] = ""
            result["tone"] = "neutral"
        else:
            result["message"] = f"你已经积累了 {jd_count} 次诊断、{review_count} 次面试练习。该出一份报告了！"
            result["cta_text"] = "生成发展报告"
            result["cta_route"] = "/report"
            result["tone"] = "celebrating"
        return result

    # report_ready — full cycle complete
    if page == "report":
        result["message"] = "报告已生成。继续做诊断和练习可以持续更新报告内容。"
        result["cta_text"] = "做新的 JD 诊断"
        result["cta_route"] = "/jd"
        result["tone"] = "neutral"
    else:
        result["message"] = "你的职业规划闭环已完成！保持练习节奏，定期更新画像和报告。"
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
    review_count = (
        db.query(func.count(InterviewReview.id))
        .join(Profile, InterviewReview.profile_id == Profile.id)
        .filter(Profile.user_id == user.id)
        .scalar() or 0
    )
    report_count = db.query(func.count(Report.id)).filter_by(user_id=user.id).scalar() or 0

    stage = compute_stage(profile_count, jd_count, review_count, report_count)

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

    # Latest review score (score lives in analysis_json)
    latest_review_score = None
    if review_count > 0:
        recent_reviews = (
            db.query(InterviewReview.analysis_json)
            .join(Profile, InterviewReview.profile_id == Profile.id)
            .filter(Profile.user_id == user.id)
            .order_by(InterviewReview.created_at.desc())
            .limit(10)
            .all()
        )
        scores = []
        for (aj,) in recent_reviews:
            try:
                s = json.loads(aj or "{}").get("score", 0)
                if s:
                    scores.append(s)
            except (json.JSONDecodeError, TypeError):
                pass
        if scores:
            latest_review_score = round(sum(scores) / len(scores))

    # JobApplication state — read-only aggregates, no business logic
    from datetime import datetime, timedelta, timezone as tz
    now = datetime.now(tz.utc)
    app_count = db.query(func.count(JobApplication.id)).filter(
        JobApplication.user_id == user.id,
        JobApplication.status != "pending",
    ).scalar() or 0
    has_applied = app_count > 0 and db.query(JobApplication).filter(
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
        review_count=review_count,
        latest_match_score=latest_match_score,
        latest_review_score=latest_review_score,
        competitiveness=competitiveness,
        app_count=app_count,
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
