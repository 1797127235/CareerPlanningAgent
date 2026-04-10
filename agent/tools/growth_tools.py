"""成长追踪工具 — GrowthAgent 使用的 @tool 函数。"""
from __future__ import annotations

from langchain_core.tools import tool


@tool
def get_dashboard_stats(profile_id: int) -> str:
    """仪表盘数据：获取用户的学习进度、诊断次数、连续天数等仪表盘统计信息。"""
    if not profile_id:
        return "需要提供画像ID才能查询仪表盘数据。"

    try:
        from backend.db import SessionLocal
        from backend.services.dashboard_service import get_dashboard_stats as _get_stats

        db = SessionLocal()
        try:
            stats = _get_stats(profile_id, db)
        finally:
            db.close()
    except Exception as e:
        return f"获取仪表盘数据时出错：{e}"

    lines = [
        f"画像 #{profile_id} 学习仪表盘：\n",
        f"  JD诊断次数: {stats.get('jd_diagnosis_count', 0)}",
        f"  面试复盘次数: {stats.get('review_count', 0)}",
        f"  连续活跃天数: {stats.get('streak_days', 0)} 天",
    ]

    checklist = stats.get("checklist_progress")
    if checklist:
        lines.append(
            f"  备战清单进度: {checklist.get('passed', 0)}/{checklist.get('total', 0)}"
            f"（{checklist.get('progress', 0)}%）— {checklist.get('jd_title', '')}"
        )

    curve = stats.get("progress_curve", [])
    if curve:
        recent = curve[-3:]
        points = [f"{p.get('type', '?')}:{p.get('score', 0)}" for p in recent]
        lines.append(f"  最近得分趋势: {' → '.join(points)}")

    recent_acts = stats.get("recent_activities", [])
    if recent_acts:
        lines.append(f"\n最近活动 ({len(recent_acts)})：")
        for act in recent_acts[:5]:
            lines.append(f"  · {act.get('title', '?')}（{act.get('date', '')[:10]}）")

    return "\n".join(lines)


@tool
def recommend_next_step(profile_id: int) -> str:
    """推荐下一步：根据用户当前阶段和进度，推荐最适合的下一步行动。"""
    if not profile_id:
        return "需要提供画像ID才能推荐下一步。"

    try:
        from backend.db import SessionLocal
        from backend.services.dashboard_service import recommend_next_step as _recommend

        db = SessionLocal()
        try:
            result = _recommend(profile_id, db)
        finally:
            db.close()
    except ValueError as e:
        return f"{e}。请先创建画像。"
    except Exception as e:
        return f"分析下一步时出错：{e}"

    header = f"当前阶段: {result['stage_label']}\n\n推荐下一步行动：\n"
    numbered = [f"{i + 1}. {r}" for i, r in enumerate(result["recommendations"])]
    return header + "\n".join(numbered)
