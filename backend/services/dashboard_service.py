# -*- coding: utf-8 -*-
"""
仪表盘数据聚合服务。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)

# China timezone for consistent local date rendering
_CN_TZ = timezone(timedelta(hours=8))


def _to_local_date(dt) -> str:
    """Convert a datetime to YYYY-MM-DD in China timezone."""
    if dt is None:
        return ""
    if not isinstance(dt, datetime):
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_CN_TZ).strftime("%Y-%m-%d")


def get_dashboard_stats(profile_id: int, db: Session) -> dict[str, Any]:
    """聚合仪表盘数据 — 仅基于当前真实存在的功能模块。"""
    from backend.models import (
        JDDiagnosis, JobApplication, InterviewRecord, ProjectRecord, Profile,
    )

    user_id = db.query(Profile.user_id).filter(Profile.id == profile_id).scalar()

    # JD 诊断次数
    jd_count = db.query(func.count(JDDiagnosis.id)).filter_by(profile_id=profile_id).scalar() or 0

    # 项目记录数
    project_count = db.query(func.count(ProjectRecord.id)).filter_by(profile_id=profile_id).scalar() or 0

    # 岗位投递数
    application_count = 0
    if user_id:
        application_count = (
            db.query(func.count(JobApplication.id)).filter_by(user_id=user_id).scalar() or 0
        )

    # 面试记录数
    interview_count = 0
    if user_id:
        interview_count = (
            db.query(func.count(InterviewRecord.id)).filter_by(user_id=user_id).scalar() or 0
        )

    # 有效操作天数 streak
    streak = _compute_streak(profile_id, db)

    # 最近活动（诊断 + 项目 + 实战 + 面试，按时间倒序，最多 10 条）
    recent = _get_recent_activities(profile_id, db, limit=10)

    return {
        "jd_diagnosis_count": jd_count,
        "project_count": project_count,
        "application_count": application_count,
        "interview_count": interview_count,
        "streak_days": streak,
        "recent_activities": recent,
    }


def _compute_streak(profile_id: int, db: Session) -> int:
    """计算有效操作天数 streak。有效 = 当天有 ≥1 次诊断、项目、实战或面试记录。"""
    from backend.models import JDDiagnosis, JobApplication, InterviewRecord, ProjectRecord, Profile

    user_id = db.query(Profile.user_id).filter(Profile.id == profile_id).scalar()

    active_dates = set()
    # Streak only needs recent history; 2 years is more than enough
    _streak_cutoff = datetime.now(timezone.utc) - timedelta(days=730)

    jd_dates = db.query(JDDiagnosis.created_at).filter(
        JDDiagnosis.profile_id == profile_id,
        JDDiagnosis.created_at >= _streak_cutoff,
    ).all()
    for (dt,) in jd_dates:
        d = _to_local_date(dt)
        if d:
            active_dates.add(d)

    project_dates = db.query(ProjectRecord.created_at).filter(
        ProjectRecord.profile_id == profile_id,
        ProjectRecord.created_at >= _streak_cutoff,
    ).all()
    for (dt,) in project_dates:
        d = _to_local_date(dt)
        if d:
            active_dates.add(d)

    if user_id:
        app_dates = db.query(JobApplication.created_at).filter(
            JobApplication.user_id == user_id,
            JobApplication.created_at >= _streak_cutoff,
        ).all()
        for (dt,) in app_dates:
            d = _to_local_date(dt)
            if d:
                active_dates.add(d)

        interview_dates = db.query(InterviewRecord.created_at).filter(
            InterviewRecord.user_id == user_id,
            InterviewRecord.created_at >= _streak_cutoff,
        ).all()
        for (dt,) in interview_dates:
            d = _to_local_date(dt)
            if d:
                active_dates.add(d)

    if not active_dates:
        return 0

    today = datetime.now(_CN_TZ).date()
    streak = 0
    current = today
    while str(current) in active_dates:
        streak += 1
        current -= timedelta(days=1)

    return streak


def _get_recent_activities(
    profile_id: int, db: Session, limit: int = 10,
) -> list[dict]:
    """获取最近活动列表（诊断 + 项目 + 实战 + 面试合并），按时间倒序。"""
    from backend.models import (
        JDDiagnosis, JobApplication, InterviewRecord, ProjectRecord, Profile,
    )

    user_id = db.query(Profile.user_id).filter(Profile.id == profile_id).scalar()
    activities: list[dict] = []

    # JD diagnoses
    jds = (
        db.query(JDDiagnosis)
        .filter_by(profile_id=profile_id)
        .order_by(JDDiagnosis.created_at.desc())
        .limit(limit)
        .all()
    )
    for jd in jds:
        activities.append({
            "type": "jd_diagnosis",
            "title": jd.jd_title or f"JD 诊断 (匹配度 {jd.match_score}%)",
            "date": jd.created_at.isoformat() if jd.created_at else "",
            "id": jd.id,
        })

    # Project records
    projects = (
        db.query(ProjectRecord)
        .filter_by(profile_id=profile_id)
        .order_by(ProjectRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    for p in projects:
        activities.append({
            "type": "project",
            "title": f"项目 · {p.name}",
            "date": p.created_at.isoformat() if p.created_at else "",
            "id": p.id,
        })

    if user_id:
        # Job applications
        apps = (
            db.query(JobApplication)
            .filter_by(user_id=user_id)
            .order_by(JobApplication.created_at.desc())
            .limit(limit)
            .all()
        )
        for a in apps:
            activities.append({
                "type": "application",
                "title": f"实战 · {a.company or '未知公司'} {a.position or ''}",
                "date": a.created_at.isoformat() if a.created_at else "",
                "id": a.id,
            })

        # Interview records
        interviews = (
            db.query(InterviewRecord)
            .filter_by(user_id=user_id)
            .order_by(InterviewRecord.created_at.desc())
            .limit(limit)
            .all()
        )
        for i in interviews:
            activities.append({
                "type": "interview",
                "title": f"面试 · {i.company or '未知公司'} {i.round or ''}",
                "date": i.created_at.isoformat() if i.created_at else "",
                "id": i.id,
            })

    activities.sort(key=lambda x: x["date"], reverse=True)
    return activities[:limit]


def get_activity_heatmap(profile_id: int, db: Session, weeks: int = 16) -> dict[str, Any]:
    """Return daily activity counts for the last N weeks, for heatmap rendering.

    Returns:
        { days: [ { date: "2026-04-08", count: 3, activities: ["项目", "JD诊断"] } ], streak: N }
    """
    from backend.models import (
        JDDiagnosis, JobApplication, InterviewRecord, ProjectRecord,
        Profile, ChatSession, CareerGoal,
    )

    cutoff = datetime.now(timezone.utc) - timedelta(weeks=weeks)

    # Resolve user_id from profile_id
    user_id = db.query(Profile.user_id).filter(Profile.id == profile_id).scalar()

    # Gather activity dates from all sources
    day_data: dict[str, dict[str, Any]] = {}

    def _add(date_str: str, label: str):
        if not date_str:
            return
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            logger.warning("Invalid date_str in activity heatmap: %r", date_str)
            return
        d = _to_local_date(dt)
        if not d:
            return
        if d not in day_data:
            day_data[d] = {"count": 0, "types": set()}
        day_data[d]["count"] += 1
        day_data[d]["types"].add(label)

    # JD diagnoses
    jds = db.query(JDDiagnosis.created_at).filter(
        JDDiagnosis.profile_id == profile_id,
        JDDiagnosis.created_at >= cutoff,
    ).all()
    for (dt,) in jds:
        if dt:
            _add(dt.isoformat(), "JD诊断")

    # Project records
    projects = db.query(ProjectRecord.created_at).filter(
        ProjectRecord.profile_id == profile_id,
        ProjectRecord.created_at >= cutoff,
    ).all()
    for (dt,) in projects:
        if dt:
            _add(dt.isoformat(), "项目")

    if user_id:
        # Job applications / pursuits
        apps = db.query(JobApplication.created_at).filter(
            JobApplication.user_id == user_id,
            JobApplication.created_at >= cutoff,
        ).all()
        for (dt,) in apps:
            if dt:
                _add(dt.isoformat(), "实战")

        # Interview records
        interviews = db.query(InterviewRecord.created_at).filter(
            InterviewRecord.user_id == user_id,
            InterviewRecord.created_at >= cutoff,
        ).all()
        for (dt,) in interviews:
            if dt:
                _add(dt.isoformat(), "面试")

        # Chat sessions (coach conversations — deduplicated per day)
        chats = db.query(ChatSession.created_at).filter(
            ChatSession.user_id == user_id,
            ChatSession.created_at >= cutoff,
        ).all()
        for (dt,) in chats:
            if dt:
                _add(dt.isoformat(), "教练对话")

        # Profile updates (resume upload / manual edit)
        profile_updated = db.query(Profile.updated_at).filter(
            Profile.user_id == user_id,
            Profile.updated_at >= cutoff,
        ).all()
        for (dt,) in profile_updated:
            if dt:
                _add(dt.isoformat(), "画像更新")

        # Career goal setting
        goals = db.query(CareerGoal.set_at).filter(
            CareerGoal.user_id == user_id,
            CareerGoal.set_at >= cutoff,
        ).all()
        for (dt,) in goals:
            if dt:
                _add(dt.isoformat(), "设定目标")

    # Build sorted list
    days = []
    for d in sorted(day_data.keys()):
        days.append({
            "date": d,
            "count": day_data[d]["count"],
            "activities": sorted(day_data[d]["types"]),
        })

    # Compute streak
    today = datetime.now(_CN_TZ).date()
    streak = 0
    current = today
    active_dates = set(day_data.keys())
    while str(current) in active_dates:
        streak += 1
        current -= timedelta(days=1)

    return {"days": days, "streak": streak}

