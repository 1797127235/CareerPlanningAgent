"""Growth insights card aggregation."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models import GrowthEntry, InterviewRecord, JDDiagnosis, JobApplication, ProjectRecord

if TYPE_CHECKING:
    from backend.models import User

logger = logging.getLogger(__name__)


def build_growth_insights(user: "User", db: Session) -> dict:
    """聚合成长洞察卡片数据 — 从各业务表自动拉取，不依赖手动输入。"""
    profile = db.query(ProjectRecord).filter(ProjectRecord.user_id == user.id).first()
    # Note: we only need profile_id for some queries; ProjectRecord is not Profile.
    # The original router used Profile. Let's fix this in the router by passing profile_id.
    # For now, accept profile_id directly to avoid DB dependency on Profile here.
    pass  # Placeholder — actual signature below


def build_growth_insights_with_profile(user: "User", db: Session, profile_id: int | None) -> dict:
    """Aggregate growth insight cards from business tables."""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    insights: list[dict] = []

    # ── 1. 近期活跃度 ──
    activity_counts: dict[str, int] = {}
    if profile_id:
        activity_counts["jd"] = (
            db.query(func.count(JDDiagnosis.id))
            .filter(JDDiagnosis.profile_id == profile_id, JDDiagnosis.created_at >= week_ago)
            .scalar() or 0
        )
        activity_counts["project"] = (
            db.query(func.count(ProjectRecord.id))
            .filter(ProjectRecord.profile_id == profile_id, ProjectRecord.created_at >= week_ago)
            .scalar() or 0
        )
        activity_counts["entry"] = (
            db.query(func.count(GrowthEntry.id))
            .filter(GrowthEntry.user_id == user.id, GrowthEntry.created_at >= week_ago)
            .scalar() or 0
        )
    activity_counts["application"] = (
        db.query(func.count(JobApplication.id))
        .filter(JobApplication.user_id == user.id, JobApplication.created_at >= week_ago)
        .scalar() or 0
    )
    activity_counts["interview"] = (
        db.query(func.count(InterviewRecord.id))
        .filter(InterviewRecord.user_id == user.id, InterviewRecord.created_at >= week_ago)
        .scalar() or 0
    )

    total_activity = sum(activity_counts.values())
    if total_activity > 0:
        parts = []
        if activity_counts.get("jd", 0) > 0:
            parts.append(f"{activity_counts['jd']} 次诊断")
        if activity_counts.get("project", 0) > 0:
            parts.append(f"{activity_counts['project']} 个项目")
        if activity_counts.get("application", 0) > 0:
            parts.append(f"{activity_counts['application']} 次投递")
        if activity_counts.get("interview", 0) > 0:
            parts.append(f"{activity_counts['interview']} 场面试")
        if activity_counts.get("entry", 0) > 0:
            parts.append(f"{activity_counts['entry']} 条记录")
        headline = f"最近 7 天：{', '.join(parts)}"
        level = "normal"
    else:
        headline = "最近 7 天没有活动记录"
        level = "warning"

    insights.append({
        "type": "activity",
        "level": level,
        "icon": "activity",
        "headline": headline,
        "detail": "",
        "link": "/growth-log",
    })

    # ── 2. 求职管道 ──
    interviewing_count = (
        db.query(func.count(JobApplication.id))
        .filter(
            JobApplication.user_id == user.id,
            JobApplication.status.in_(["screening", "scheduled", "interviewed"]),
        )
        .scalar() or 0
    )
    pending_debrief = (
        db.query(func.count(InterviewRecord.id))
        .filter(
            InterviewRecord.user_id == user.id,
            InterviewRecord.result == "pending",
        )
        .scalar() or 0
    )
    if interviewing_count > 0 or pending_debrief > 0:
        parts = []
        if interviewing_count > 0:
            parts.append(f"{interviewing_count} 家在流程中")
        if pending_debrief > 0:
            parts.append(f"{pending_debrief} 场待复盘")
        insights.append({
            "type": "pipeline",
            "level": "highlight" if interviewing_count > 0 else "normal",
            "icon": "briefcase",
            "headline": "求职进展：" + "，".join(parts),
            "detail": "",
            "link": "/pursuits",
        })

    # ── 3. 计划状态 ──
    pending_plans = (
        db.query(GrowthEntry)
        .filter(
            GrowthEntry.user_id == user.id,
            GrowthEntry.is_plan == True,
            GrowthEntry.status == "pending",
        )
        .all()
    )
    if pending_plans:
        overdue = [p for p in pending_plans if p.due_at and p.due_at < now]
        headline = f"{len(pending_plans)} 条待完成计划"
        detail = f"其中 {len(overdue)} 条已逾期" if overdue else ""
        insights.append({
            "type": "plan",
            "level": "warning" if overdue else "normal",
            "icon": "check-circle",
            "headline": headline,
            "detail": detail,
            "link": "/growth-log?filter=plan",
        })

    # ── 4. 最近诊断 ──
    if profile_id:
        latest_jd = (
            db.query(JDDiagnosis)
            .filter(JDDiagnosis.profile_id == profile_id)
            .order_by(JDDiagnosis.created_at.desc())
            .first()
        )
        if latest_jd:
            match = latest_jd.match_score or 0
            try:
                result = json.loads(latest_jd.result_json or "{}")
                gap_skills = result.get("gap_skills", [])[:3]
            except Exception:
                gap_skills = []
            detail = f"缺口：{', '.join(gap_skills)}" if gap_skills else ""
            insights.append({
                "type": "diagnosis",
                "level": "normal",
                "icon": "target",
                "headline": f"最近诊断：{latest_jd.jd_title or '未命名岗位'} · 匹配度 {match}%",
                "detail": detail,
                "link": "/jd-diagnosis",
            })

    # ── 5. 最近面试 ──
    latest_interview = (
        db.query(InterviewRecord)
        .filter(InterviewRecord.user_id == user.id)
        .order_by(InterviewRecord.interview_at.desc())
        .first()
    )
    if latest_interview:
        rating_map = {"good": "发挥好", "medium": "一般", "bad": "发挥差"}
        rating = rating_map.get(latest_interview.self_rating or "", "")
        headline = f"最近面试：{latest_interview.company or '未知公司'} {latest_interview.round or ''}"
        if rating:
            headline += f" · {rating}"
        detail = ""
        if latest_interview.ai_analysis:
            actions = latest_interview.ai_analysis.get("action_items", [])
            if actions:
                detail = f"Coach 建议：{actions[0]}"
        insights.append({
            "type": "interview",
            "level": "highlight" if latest_interview.self_rating == "good" else "normal",
            "icon": "mic",
            "headline": headline,
            "detail": detail,
            "link": "/growth-log",
        })

    return {"insights": insights}
