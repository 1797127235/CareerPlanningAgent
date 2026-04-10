"""练习工具 — PracticeAgent 使用的 @tool 函数。

全部委托 PracticeService，不直接访问底层模块。
"""
from __future__ import annotations

from langchain_core.tools import tool


@tool
def pick_question(profile_id: int, skill_tag: str = "") -> str:
    """出题：从题库中按技能标签抽取一道面试题。不传 skill_tag 则随机抽题。"""
    if not profile_id:
        return "需要提供画像ID。"

    try:
        from backend.db import SessionLocal
        from backend.services.practice_service import PracticeService

        svc = PracticeService()
        db = SessionLocal()
        try:
            tags = [skill_tag] if skill_tag else None
            questions = svc.pick_questions(db, skill_tags=tags, count=1)
        finally:
            db.close()
    except Exception as e:
        return f"抽题时出错：{e}"

    if not questions:
        hint = f"「{skill_tag}」" if skill_tag else "题库"
        return f"{hint}中暂无题目。可用 list_question_tags 查看可用标签。"

    q = questions[0]
    difficulty_map = {"easy": "🟢 基础", "medium": "🟡 中等", "hard": "🔴 困难"}
    diff_label = difficulty_map.get(q.get("difficulty", ""), q.get("difficulty", ""))
    lines = [
        f"📋 面试题（{diff_label}）",
        f"技能方向：{q.get('focus_skill', '通用')}",
        f"题目类型：{q.get('type', '技术')}",
        "",
        q.get("question", ""),
    ]
    return "\n".join(lines)


@tool
def evaluate_answer(question: str, answer: str, target_job: str = "") -> str:
    """评分：评估用户对面试题的回答，给出分数和改进建议。"""
    if not question or not answer:
        return "需要提供题目和回答。"

    try:
        from backend.services.practice_service import PracticeService

        svc = PracticeService()
        result = svc.analyze_answer(
            question=question,
            answer=answer,
            target_job=target_job or "通用技术岗位",
        )
    except Exception as e:
        return f"评分时出错：{e}"

    score = result.get("score", 0)
    lines = [f"得分：{score}/10"]

    strengths = result.get("strengths", [])
    if strengths:
        lines.append("\n亮点：")
        lines.extend(f"  ✅ {s}" for s in strengths)

    weaknesses = result.get("weaknesses", [])
    if weaknesses:
        lines.append("\n改进：")
        lines.extend(f"  ⚠️ {w}" for w in weaknesses)

    feedback = result.get("overall_feedback", "")
    if feedback:
        lines.append(f"\n总评：{feedback}")

    return "\n".join(lines)


@tool
def review_practice_history(profile_id: int) -> str:
    """面试复盘：分析用户的历史面试练习记录，找出薄弱点和进步趋势。"""
    if not profile_id:
        return "需要提供画像ID。"

    try:
        import json
        from backend.db import SessionLocal
        from backend.db_models import InterviewReview

        db = SessionLocal()
        try:
            reviews = (
                db.query(InterviewReview)
                .filter_by(profile_id=profile_id)
                .order_by(InterviewReview.created_at.desc())
                .limit(20)
                .all()
            )
        finally:
            db.close()
    except Exception as e:
        return f"查询练习记录时出错：{e}"

    if not reviews:
        return "暂无面试练习记录。建议先练几道题积累数据。"

    total = len(reviews)
    scores = []
    strength_counts: dict[str, int] = {}
    weakness_counts: dict[str, int] = {}

    for r in reviews:
        try:
            analysis = json.loads(r.analysis_json or "{}")
        except (json.JSONDecodeError, TypeError):
            analysis = {}

        score = analysis.get("score", 0)
        if score:
            scores.append(score)

        for s in analysis.get("strengths", []):
            strength_counts[s] = strength_counts.get(s, 0) + 1
        for w in analysis.get("weaknesses", []):
            weakness_counts[w] = weakness_counts.get(w, 0) + 1

    lines = [f"面试练习复盘（共 {total} 题）：\n"]

    if scores:
        avg = sum(scores) / len(scores)
        recent_avg = sum(scores[:5]) / min(5, len(scores))
        lines.append(f"平均得分: {avg:.1f}/10")
        lines.append(f"最近5题平均: {recent_avg:.1f}/10")
        trend = "进步" if recent_avg > avg else "持平" if abs(recent_avg - avg) < 0.5 else "需加油"
        lines.append(f"趋势: {trend}")

    if weakness_counts:
        top_weak = sorted(weakness_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        lines.append(f"\n最常见的薄弱点:")
        for w, cnt in top_weak:
            lines.append(f"  - {w}（出现 {cnt} 次）")

    if strength_counts:
        top_strong = sorted(strength_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        lines.append(f"\n稳定的优势:")
        for s, cnt in top_strong:
            lines.append(f"  - {s}（出现 {cnt} 次）")

    return "\n".join(lines)


@tool
def list_question_tags() -> str:
    """题库标签：列出所有可用的技能标签及题目数量。"""
    try:
        from backend.db import SessionLocal
        from backend.services.practice_service import PracticeService

        svc = PracticeService()
        db = SessionLocal()
        try:
            tags = svc.list_question_tags(db)
        finally:
            db.close()
    except Exception as e:
        return f"查询标签时出错：{e}"

    if not tags:
        return "题库暂无题目。"

    lines = ["可用技能标签："]
    for t in tags:
        lines.append(f"  · {t['tag']}（{t['count']}题）")
    lines.append(f"\n共 {sum(t['count'] for t in tags)} 道题目")
    return "\n".join(lines)
