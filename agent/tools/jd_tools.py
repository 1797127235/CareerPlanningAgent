"""JD 诊断工具 — JDAgent 使用的 @tool 函数。"""
from __future__ import annotations

import json
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _save_jd_coach_result(
    jd_text: str, match_score: int, matched: list, gaps: list, jd_title: str,
    user_id: int | None = None,
) -> int | None:
    """Save JD diagnosis as a CoachResult. Returns the result ID or None."""
    try:
        from backend.db import SessionLocal
        from backend.db_models import CoachResult, JDDiagnosis

        db = SessionLocal()
        try:
            # If no user_id passed, try the latest JD diagnosis as fallback
            if not user_id:
                latest = (
                    db.query(JDDiagnosis)
                    .order_by(JDDiagnosis.created_at.desc())
                    .first()
                )
                user_id = latest.user_id if latest else None
            if not user_id:
                return None

            coach_result = CoachResult(
                user_id=user_id,
                result_type="jd_diagnosis",
                title=jd_title or jd_text[:40] + "...",
                summary=f"匹配度 {match_score}%，匹配 {len(matched)} 项技能，缺口 {len(gaps)} 项",
                detail_json=json.dumps({
                    "_structured": True,
                    "match_score": match_score,
                    "matched_skills": matched,
                    "gap_skills": gaps,
                    "jd_title": jd_title,
                }, ensure_ascii=False),
                metadata_json=json.dumps({
                    "match_score": match_score,
                    "gap_count": len(gaps),
                    "matched_count": len(matched),
                }, ensure_ascii=False),
            )
            db.add(coach_result)
            db.commit()
            return coach_result.id
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to save JD CoachResult")
        return None


@tool
def diagnose_jd(jd_text: str, profile_json: str) -> str:
    """JD诊断：分析岗位JD与用户画像的匹配度，识别技能缺口和改进方向。"""
    if not jd_text or not jd_text.strip():
        return "请提供岗位JD文本内容。"

    try:
        profile = json.loads(profile_json)
    except (json.JSONDecodeError, TypeError):
        return "画像数据格式错误，请提供有效的JSON字符串。"

    try:
        from backend.services.jd_service import JDService

        svc = JDService()
        result = svc.diagnose(jd_text, profile)
    except Exception as e:
        return f"JD诊断时出错：{e}"

    match_score = result.get("match_score", 0)
    matched = result.get("matched_skills", [])
    gaps = result.get("gap_skills", [])

    # Save structured result to CoachResult DB table
    # Try to get user_id from the JDDiagnosis that was just created by JDService
    _user_id = None
    try:
        from backend.db import SessionLocal as _SL
        from backend.db_models import JDDiagnosis as _JD
        _db = _SL()
        _latest = _db.query(_JD).order_by(_JD.created_at.desc()).first()
        if _latest:
            _user_id = _latest.user_id
        _db.close()
    except Exception:
        pass

    coach_result_id = _save_jd_coach_result(
        jd_text, match_score, matched, gaps, result.get("jd_title", ""),
        user_id=_user_id,
    )

    # Return summary for LLM + result_id for card
    gap_names = [g.get("skill", "?") for g in gaps[:5]]
    lines = [
        f"JD匹配度: {match_score}%",
        f"已匹配技能: {', '.join(matched[:5]) if matched else '无'}",
        f"技能缺口: {', '.join(gap_names) if gap_names else '无'}",
    ]
    if coach_result_id:
        lines.append(f"[COACH_RESULT_ID:{coach_result_id}]")

    return "\n".join(lines)


@tool
def get_jd_history(profile_id: int) -> str:
    """JD诊断历史：查看用户历史JD诊断记录。"""
    try:
        from backend.db import SessionLocal
        from backend.db_models import JDDiagnosis

        db = SessionLocal()
        try:
            records = (
                db.query(JDDiagnosis)
                .filter_by(profile_id=profile_id)
                .order_by(JDDiagnosis.created_at.desc())
                .limit(10)
                .all()
            )
        finally:
            db.close()
    except Exception as e:
        return f"查询JD诊断历史时出错：{e}"

    if not records:
        return f"画像 #{profile_id} 暂无JD诊断记录。"

    lines = [f"最近 {len(records)} 条JD诊断记录：\n"]
    for i, r in enumerate(records, 1):
        title = r.jd_title or "未命名JD"
        score = r.match_score
        date = r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "N/A"
        lines.append(f"  {i}. {title} — 匹配度 {score}%（{date}）")

    return "\n".join(lines)
