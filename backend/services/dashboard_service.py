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

# Normalize English dimension keys (from mock interview) to Chinese labels (from single-Q review)
_KEY_TO_LABEL = {
    "technical_depth": "技术深度",
    "expression": "表达清晰度",
    "project_experience": "项目经验",
    "adaptability": "应变能力",
    "answer_structure": "回答结构性",
    "example_ability": "举例能力",
}


def _parse_analysis(raw: str | None) -> dict:
    """Safely parse analysis_json, shared by InterviewReview and MockInterviewSession."""
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def get_dashboard_stats(profile_id: int, db: Session) -> dict[str, Any]:
    """聚合仪表盘数据。"""
    from backend.db_models import (
        JDDiagnosis, InterviewReview, InterviewChecklist, MockInterviewSession,
    )

    # JD 诊断次数
    jd_count = db.query(func.count(JDDiagnosis.id)).filter_by(profile_id=profile_id).scalar() or 0

    # 面试复盘次数（单题）
    review_count = db.query(func.count(InterviewReview.id)).filter_by(profile_id=profile_id).scalar() or 0

    # 模拟面试 — 一次查出，后续函数共享，避免重复查询
    mock_sessions = (
        db.query(MockInterviewSession)
        .filter_by(profile_id=profile_id, status="finished")
        .order_by(MockInterviewSession.finished_at.asc())
        .all()
    )
    mock_count = len(mock_sessions)

    # 备战清单进度（最新的一个）
    checklist = (
        db.query(InterviewChecklist)
        .filter_by(profile_id=profile_id)
        .order_by(InterviewChecklist.created_at.desc())
        .first()
    )
    checklist_progress = None
    if checklist:
        items = checklist.items or []
        total = len(items)
        passed = sum(1 for i in items if i.get("status") in ("can_answer", "learned"))
        checklist_progress = {
            "total": total,
            "passed": passed,
            "progress": round(passed / total * 100) if total else 0,
            "jd_title": checklist.jd_title,
        }

    # 有效操作天数 streak
    streak = _compute_streak(profile_id, db, mock_sessions)

    # 最近活动（诊断 + 复盘 + 模拟面试合并，按时间倒序，最多 10 条）
    recent = _get_recent_activities(profile_id, db, mock_sessions, limit=10)

    # 进步曲线
    progress_curve = _get_progress_curve(profile_id, db, mock_sessions)

    # 维度聚合
    dimension_summary = _get_dimension_summary(profile_id, db, mock_sessions)

    return {
        "jd_diagnosis_count": jd_count,
        "review_count": review_count + mock_count,
        "checklist_progress": checklist_progress,
        "streak_days": streak,
        "recent_activities": recent,
        "progress_curve": progress_curve,
        "dimension_summary": dimension_summary,
    }


def _compute_streak(profile_id: int, db: Session, mock_sessions: list) -> int:
    """计算有效操作天数 streak。有效 = 当天有 ≥1 次诊断、复盘或模拟面试。"""
    from backend.db_models import JDDiagnosis, InterviewReview

    jd_dates = (
        db.query(func.date(JDDiagnosis.created_at))
        .filter_by(profile_id=profile_id)
        .all()
    )
    review_dates = (
        db.query(func.date(InterviewReview.created_at))
        .filter_by(profile_id=profile_id)
        .all()
    )

    active_dates = set()
    for (d,) in jd_dates:
        if d:
            active_dates.add(str(d))
    for (d,) in review_dates:
        if d:
            active_dates.add(str(d))
    for m in mock_sessions:
        if m.finished_at:
            active_dates.add(str(m.finished_at.date()))

    if not active_dates:
        return 0

    today = datetime.now(timezone.utc).date()
    streak = 0
    current = today
    while str(current) in active_dates:
        streak += 1
        current -= timedelta(days=1)

    return streak


def _get_recent_activities(
    profile_id: int, db: Session, mock_sessions: list, limit: int = 10,
) -> list[dict]:
    """获取最近活动列表（诊断 + 单题复盘 + 模拟面试合并）。"""
    from backend.db_models import JDDiagnosis, InterviewReview

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

    # Single-question reviews
    reviews = (
        db.query(InterviewReview)
        .filter_by(profile_id=profile_id)
        .order_by(InterviewReview.created_at.desc())
        .limit(limit)
        .all()
    )
    for r in reviews:
        analysis = _parse_analysis(r.analysis_json)
        activities.append({
            "type": "interview_review",
            "title": f"面试复盘 · {r.target_job or '未指定岗位'} ({analysis.get('score', 0)}分)",
            "date": r.created_at.isoformat() if r.created_at else "",
            "id": r.id,
        })

    # Mock interview sessions (already filtered to finished)
    for m in mock_sessions:
        analysis = _parse_analysis(m.analysis_json)
        score = analysis.get("overall_score", 0)
        activities.append({
            "type": "mock_interview",
            "title": f"模拟面试 · {m.target_job or '未指定岗位'} ({score}分)",
            "date": (m.finished_at or m.created_at).isoformat(),
            "id": m.id,
        })

    activities.sort(key=lambda x: x["date"], reverse=True)
    return activities[:limit]


def _extract_dim_scores(dims: list) -> dict[str, int]:
    """Extract dimension scores from analysis dimensions list, normalizing keys to Chinese labels."""
    result = {}
    for d in dims:
        if isinstance(d, dict) and "score" in d:
            label = d.get("name") or _KEY_TO_LABEL.get(d.get("key", ""), d.get("label", ""))
            if label:
                result[label] = d["score"]
    return result


def _get_progress_curve(profile_id: int, db: Session, mock_sessions: list) -> list[dict]:
    """获取进步曲线数据（JD 匹配度 + 单题复盘 + 模拟面试的时间序列）。"""
    from backend.db_models import JDDiagnosis, InterviewReview

    points: list[dict] = []

    # JD diagnosis scores
    jds = (
        db.query(JDDiagnosis)
        .filter_by(profile_id=profile_id)
        .order_by(JDDiagnosis.created_at.asc())
        .all()
    )
    for jd in jds:
        points.append({
            "type": "jd",
            "date": jd.created_at.isoformat() if jd.created_at else "",
            "score": jd.match_score,
        })

    # Single-question review scores
    reviews = (
        db.query(InterviewReview)
        .filter_by(profile_id=profile_id)
        .order_by(InterviewReview.created_at.asc())
        .all()
    )
    for r in reviews:
        analysis = _parse_analysis(r.analysis_json)
        if not analysis:
            continue
        points.append({
            "type": "review",
            "date": r.created_at.isoformat() if r.created_at else "",
            "score": analysis.get("score", 0),
            "dimensions": _extract_dim_scores(analysis.get("dimensions", [])),
        })

    # Mock interview scores
    for m in mock_sessions:
        analysis = _parse_analysis(m.analysis_json)
        if not analysis:
            continue
        points.append({
            "type": "review",  # same type so frontend curves render uniformly
            "date": (m.finished_at or m.created_at).isoformat(),
            "score": analysis.get("overall_score", 0),
            "dimensions": _extract_dim_scores(analysis.get("dimensions", [])),
        })

    points.sort(key=lambda x: x["date"])
    return points


def _get_dimension_summary(
    profile_id: int, db: Session, mock_sessions: list,
) -> dict[str, Any]:
    """聚合维度评分数据：每个维度的平均分 + 最弱维度。"""
    from backend.db_models import InterviewReview

    reviews = (
        db.query(InterviewReview)
        .filter_by(profile_id=profile_id)
        .order_by(InterviewReview.created_at.asc())
        .all()
    )

    # Collect all analysis blobs from both sources
    all_analyses = [_parse_analysis(r.analysis_json) for r in reviews]
    all_analyses += [_parse_analysis(m.analysis_json) for m in mock_sessions]

    dim_scores: dict[str, list[int]] = {}
    for analysis in all_analyses:
        for d in analysis.get("dimensions", []):
            if not isinstance(d, dict) or "score" not in d:
                continue
            label = d.get("name") or _KEY_TO_LABEL.get(d.get("key", ""), d.get("label", ""))
            if label:
                dim_scores.setdefault(label, []).append(d["score"])

    if not dim_scores:
        return {"dimensions": [], "weakest": []}

    dim_avgs = []
    for name, scores in dim_scores.items():
        avg = round(sum(scores) / len(scores))
        dim_avgs.append({
            "name": name,
            "avg_score": avg,
            "count": len(scores),
            "trend": _dim_trend(scores),
        })

    dim_avgs.sort(key=lambda x: x["avg_score"])
    weakest = [d["name"] for d in dim_avgs[:2] if d["avg_score"] < 80]

    return {
        "dimensions": dim_avgs,
        "weakest": weakest,
    }


def recommend_next_step(profile_id: int, db: Session) -> dict[str, Any]:
    """根据用户当前阶段和进度，推荐最适合的下一步行动。

    Returns
    -------
    dict with ``stage``, ``stage_label``, ``recommendations`` (list[str]).
    Raises ValueError if profile not found.
    """
    from backend.db_models import Profile, CareerGoal, JDDiagnosis

    profile = db.query(Profile).filter_by(id=profile_id).first()
    if profile is None:
        raise ValueError(f"未找到画像 #{profile_id}")

    # Check career goal
    goal = (
        db.query(CareerGoal)
        .filter_by(profile_id=profile_id, is_active=True)
        .first()
    )

    # Check JD diagnosis history
    jd_count = (
        db.query(JDDiagnosis)
        .filter_by(profile_id=profile_id)
        .count()
    )

    stats = get_dashboard_stats(profile_id, db)

    # Determine user stage and recommend
    recommendations: list[str] = []

    if goal is None:
        stage = "no_goal"
        recommendations.append("探索岗位图谱，了解不同岗位的发展前景")
        recommendations.append("完成图谱定位，找到你当前最匹配的位置")
        recommendations.append("查看逃生路线，设定职业目标")
    elif jd_count == 0:
        stage = "has_goal"
        recommendations.append(f"你的目标是「{goal.target_label}」，下一步做JD诊断")
        recommendations.append("找一份目标岗位的真实JD，做匹配度分析")
        recommendations.append("根据缺口技能制定学习计划")
    else:
        stage = "active"
        streak = stats.get("streak_days", 0)
        review_count = stats.get("review_count", 0)
        checklist = stats.get("checklist_progress")

        if checklist and checklist.get("progress", 0) < 80:
            recommendations.append(
                f"继续攻克备战清单（进度 {checklist.get('progress', 0)}%）"
            )
        if review_count < 5:
            recommendations.append("做更多面试练习或模拟面试，积累实战经验")
        if streak == 0:
            recommendations.append("今天还没有活动记录，保持学习节奏")
        else:
            recommendations.append(f"已连续活跃 {streak} 天，继续保持")

    if not recommendations:
        recommendations.append("继续保持学习节奏，定期回顾和更新画像数据。")

    stage_names = {
        "no_goal": "未设目标",
        "has_goal": "已设目标",
        "active": "积极学习中",
    }

    return {
        "stage": stage,
        "stage_label": stage_names.get(stage, stage),
        "recommendations": recommendations,
    }


def get_activity_heatmap(profile_id: int, db: Session, weeks: int = 16) -> dict[str, Any]:
    """Return daily activity counts for the last N weeks, for heatmap rendering.

    Returns:
        { days: [ { date: "2026-04-08", count: 3, activities: ["学习", "JD诊断"] } ], streak: N }
    """
    from backend.db_models import JDDiagnosis, InterviewReview, MockInterviewSession, LearningProgress

    cutoff = datetime.now(timezone.utc) - timedelta(weeks=weeks)

    # Gather activity dates from all sources
    day_data: dict[str, dict[str, Any]] = {}

    def _add(date_str: str, label: str):
        if not date_str:
            return
        d = date_str[:10]  # YYYY-MM-DD
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

    # Interview reviews
    reviews = db.query(InterviewReview.created_at).filter(
        InterviewReview.profile_id == profile_id,
        InterviewReview.created_at >= cutoff,
    ).all()
    for (dt,) in reviews:
        if dt:
            _add(dt.isoformat(), "面试练习")

    # Mock interviews
    mocks = db.query(MockInterviewSession.finished_at).filter(
        MockInterviewSession.profile_id == profile_id,
        MockInterviewSession.status == "finished",
        MockInterviewSession.finished_at >= cutoff,
    ).all()
    for (dt,) in mocks:
        if dt:
            _add(dt.isoformat(), "模拟面试")

    # Learning progress
    learns = db.query(LearningProgress.completed_at).filter(
        LearningProgress.profile_id == profile_id,
        LearningProgress.completed == True,
        LearningProgress.completed_at >= cutoff,
    ).all()
    for (dt,) in learns:
        if dt:
            _add(dt.isoformat(), "学习")

    # Build sorted list
    days = []
    for d in sorted(day_data.keys()):
        days.append({
            "date": d,
            "count": day_data[d]["count"],
            "activities": sorted(day_data[d]["types"]),
        })

    # Compute streak
    today = datetime.now(timezone.utc).date()
    streak = 0
    current = today
    active_dates = set(day_data.keys())
    while str(current) in active_dates:
        streak += 1
        current -= timedelta(days=1)

    return {"days": days, "streak": streak}


def _dim_trend(scores: list[int]) -> str:
    """Compare last 3 scores vs earlier scores. Needs ≥4 data points."""
    if len(scores) < 4:
        return "flat"
    recent = scores[-3:]
    earlier = scores[:-3]
    recent_avg = sum(recent) / len(recent)
    earlier_avg = sum(earlier) / len(earlier)
    if recent_avg > earlier_avg + 3:
        return "up"
    if recent_avg < earlier_avg - 3:
        return "down"
    return "flat"
