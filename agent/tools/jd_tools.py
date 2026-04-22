"""JD 诊断工具 — JDAgent 使用的 @tool 函数。"""
from __future__ import annotations

import json
import logging
from contextvars import ContextVar

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# ── ContextVar 注入（supervisor 在调用 jd_agent 前设置）────────────────────────
_injected_profile: ContextVar[dict | None] = ContextVar('_injected_profile', default=None)
_injected_user_id: ContextVar[int | None] = ContextVar('_injected_user_id', default=None)


def _save_jd_coach_result(
    jd_text: str, match_score: int, matched: list, gaps: list, jd_title: str,
    user_id: int | None = None,
    company: str = "",
    job_url: str = "",
) -> int | None:
    """Save JD diagnosis as a CoachResult. Returns the result ID or None."""
    try:
        from backend.db import SessionLocal
        from backend.models import CoachResult, JDDiagnosis

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

            # Build display title: prefer "公司 - 岗位" if company available
            display_title = jd_title or (jd_text[:40] + "...")
            if company and jd_title and company not in jd_title:
                display_title = f"{company} · {jd_title}"

            coach_result = CoachResult(
                user_id=user_id,
                result_type="jd_diagnosis",
                title=display_title,
                summary=f"匹配度 {match_score}%，匹配 {len(matched)} 项技能，缺口 {len(gaps)} 项",
                detail_json=json.dumps({
                    "_structured": True,
                    "match_score": match_score,
                    "matched_skills": matched,
                    "gap_skills": gaps,
                    "jd_title": jd_title,
                    "company": company,
                    "job_url": job_url,
                }, ensure_ascii=False),
                metadata_json=json.dumps({
                    "match_score": match_score,
                    "gap_count": len(gaps),
                    "matched_count": len(matched),
                    "company": company,
                    "job_url": job_url,
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


def _auto_link_diagnosis_to_application(jd_title: str, user_id: int) -> None:
    """Link the latest JDDiagnosis to a matching JobApplication (by company name hint)."""
    if not user_id or not jd_title:
        return
    try:
        from backend.db import SessionLocal
        from backend.models import JobApplication, JDDiagnosis

        db = SessionLocal()
        try:
            latest_diag = (
                db.query(JDDiagnosis)
                .filter_by(user_id=user_id)
                .order_by(JDDiagnosis.created_at.desc())
                .first()
            )
            if not latest_diag:
                return

            # Extract company hint: first token of jd_title (e.g. "腾讯-后端工程师" → "腾讯")
            company_hint = jd_title.replace('—', '-').replace('–', '-').split('-')[0].strip().split()[0]
            if len(company_hint) < 2:
                return

            # Find the most recent unlinked application matching the company
            app = (
                db.query(JobApplication)
                .filter(
                    JobApplication.user_id == user_id,
                    JobApplication.jd_diagnosis_id == None,
                    JobApplication.company.ilike(f"%{company_hint}%"),
                )
                .order_by(JobApplication.created_at.desc())
                .first()
            )
            if app:
                app.jd_diagnosis_id = latest_diag.id
                db.commit()
                logger.info(
                    "Auto-linked JDDiagnosis %s → JobApplication %s (%s)",
                    latest_diag.id, app.id, app.company,
                )
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to auto-link diagnosis to application")


@tool
def diagnose_jd(jd_text: str) -> str:
    """JD诊断：分析岗位JD与用户画像的匹配度，识别技能缺口和改进方向。"""
    if not jd_text or not jd_text.strip():
        return "请提供岗位JD文本内容。"

    # Read injected context (set by supervisor before jd_agent runs)
    profile = _injected_profile.get()
    user_id = _injected_user_id.get()

    # Fallback: load profile from DB if ContextVar not set
    if profile is None and user_id:
        try:
            from backend.db import SessionLocal
            from backend.models import Profile as _Profile
            db = SessionLocal()
            try:
                p = (
                    db.query(_Profile)
                    .filter_by(user_id=user_id)
                    .order_by(_Profile.updated_at.desc())
                    .first()
                )
                profile = json.loads(p.profile_json or "{}") if p else {}
            finally:
                db.close()
        except Exception:
            profile = {}

    if not profile:
        return "未找到用户画像，请先上传简历建立画像后再进行 JD 诊断。"

    try:
        from backend.services.jd_service import JDService
        svc = JDService()
        result = svc.diagnose(jd_text, profile)
    except Exception as e:
        return f"JD诊断时出错：{e}"

    match_score = result.get("match_score", 0)
    matched = result.get("matched_skills", [])
    gaps = result.get("gap_skills", [])
    jd_title = result.get("jd_title", "")

    # Fallback user_id from latest JDDiagnosis if still unknown
    if not user_id:
        try:
            from backend.db import SessionLocal as _SL
            from backend.models import JDDiagnosis as _JD
            _db = _SL()
            _latest = _db.query(_JD).order_by(_JD.created_at.desc()).first()
            if _latest:
                user_id = _latest.user_id
            _db.close()
        except Exception:
            pass

    coach_result_id = _save_jd_coach_result(
        jd_text, match_score, matched, gaps, jd_title,
        user_id=user_id,
    )

    # Auto-link to existing JobApplication by company name
    if user_id and jd_title:
        _auto_link_diagnosis_to_application(jd_title, user_id)


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
        from backend.models import JDDiagnosis

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
