"""成长追踪工具 — GrowthAgent 使用的 @tool 函数。"""
from __future__ import annotations

from contextvars import ContextVar

from langchain_core.tools import tool

# Injected by supervisor before calling growth_agent
_injected_user_id: ContextVar[int | None] = ContextVar('_growth_user_id', default=None)


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
        f"  项目记录数: {stats.get('project_count', 0)}",
        f"  岗位追踪数: {stats.get('application_count', 0)}",
        f"  面试记录数: {stats.get('interview_count', 0)}",
        f"  连续活跃天数: {stats.get('streak_days', 0)} 天",
    ]

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


@tool
def get_interview_records(company: str = "") -> str:
    """查询用户的面试记录，包括每轮题目、回答要点和 AI 复盘。
    可按公司名过滤。当用户问"我的面试"、"某家公司的面试情况"、"面试表现"时调用。
    """
    user_id = _injected_user_id.get()
    if not user_id:
        return "无法获取用户信息。"

    try:
        from backend.db import SessionLocal
        from backend.models import InterviewRecord

        db = SessionLocal()
        try:
            q = db.query(InterviewRecord).filter_by(user_id=user_id)
            if company:
                q = q.filter(InterviewRecord.company.contains(company))
            records = q.order_by(InterviewRecord.created_at.desc()).limit(8).all()
        finally:
            db.close()
    except Exception as e:
        return f"查询面试记录时出错：{e}"

    if not records:
        return f"没有找到{'「' + company + '」的' if company else ''}面试记录。"

    lines = [f"面试记录（{len(records)} 轮）：\n"]
    rating_map = {"good": "发挥好", "medium": "正常", "bad": "较差"}

    for r in records:
        rating = rating_map.get(r.self_rating or "", "")
        date_str = r.interview_at or (r.created_at.strftime("%m/%d") if r.created_at else "")
        header = f"【{r.company} · {r.round}】{' · ' + rating if rating else ''} ({date_str})"
        lines.append(header)

        # Q/A summary (first 2 questions)
        content = r.content_summary or ""
        import re
        questions = re.findall(r'Q\d+:\s*(.+?)(?=\nA\d+:|\nQ\d+:|$)', content, re.DOTALL)
        for i, q_text in enumerate(questions[:2]):
            lines.append(f"  Q{i+1}: {q_text.strip()[:60]}{'…' if len(q_text.strip()) > 60 else ''}")

        # AI analysis summary
        if r.ai_analysis:
            overall = r.ai_analysis.get("overall", "")
            if overall:
                lines.append(f"  AI复盘: {overall[:80]}{'…' if len(overall) > 80 else ''}")

        lines.append("")

    return "\n".join(lines)


@tool
def get_project_progress(project_name: str = "") -> str:
    """查询用户的项目进展记录。可按项目名过滤，不传则返回所有进行中的项目的最新进展。
    当用户问"我的项目"、"项目进展"、"某个项目做得怎样"时调用。
    """
    user_id = _injected_user_id.get()
    if not user_id:
        return "无法获取用户信息。"

    try:
        from backend.db import SessionLocal
        from backend.models import ProjectRecord, ProjectLog

        db = SessionLocal()
        try:
            q = db.query(ProjectRecord).filter_by(user_id=user_id)
            if project_name:
                q = q.filter(ProjectRecord.name.contains(project_name))
            else:
                q = q.filter(ProjectRecord.status == "in_progress")
            projects = q.order_by(ProjectRecord.updated_at.desc()).limit(5).all()

            result_lines = []
            for p in projects:
                status_map = {"planning": "规划中", "in_progress": "进行中", "completed": "已完成"}
                skills_str = "、".join((p.skills_used or [])[:4])
                result_lines.append(f"【{p.name}】{status_map.get(p.status, p.status)}")
                if skills_str:
                    result_lines.append(f"  技术栈: {skills_str}")
                if p.description:
                    result_lines.append(f"  简介: {p.description[:60]}{'…' if len(p.description) > 60 else ''}")

                # Latest 3 logs
                logs = (
                    db.query(ProjectLog)
                    .filter_by(project_id=p.id)
                    .order_by(ProjectLog.created_at.desc())
                    .limit(3)
                    .all()
                )
                if logs:
                    result_lines.append("  最近进展:")
                    task_status_map = {"done": "✓", "in_progress": "→", "blocked": "✗"}
                    for log in logs:
                        mark = task_status_map.get(log.task_status or "done", "")
                        result_lines.append(f"    {mark} {log.content[:50]}{'…' if len(log.content) > 50 else ''}")
                result_lines.append("")
        finally:
            db.close()
    except Exception as e:
        return f"查询项目进展时出错：{e}"

    if not result_lines:
        return f"没有找到{'「' + project_name + '」的' if project_name else '进行中的'}项目。"

    return "\n".join(result_lines)
