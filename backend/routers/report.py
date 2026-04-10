"""Report router — generate, edit, polish, and retrieve career reports."""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import get_db
from backend.db_models import Profile, Report, User
from backend.services.report_service import ReportService

logger = logging.getLogger(__name__)

router = APIRouter()
_report_svc = ReportService()


@router.post("/generate")
def generate_report(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a new report (profile inferred from current user)."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(404, "请先上传简历建立画像")
    profile_id = profile.id

    result = _report_svc.generate_report(profile_id, db)
    return result


@router.get("/")
def list_reports(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List reports for the current user."""
    rows = (
        db.query(Report)
        .filter(Report.user_id == user.id)
        .order_by(Report.updated_at.desc())
        .all()
    )
    result = []
    for r in rows:
        data = json.loads(r.data_json or "{}")
        result.append({
            "id": r.id,
            "report_key": r.report_key,
            "title": r.title,
            "summary": r.summary,
            "created_at": str(r.created_at),
            "profile_id": data.get("profile_id"),
        })
    return result


@router.get("/{report_id}")
def get_report(
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full report detail by id."""
    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.user_id == user.id)
        .first()
    )
    if not report:
        raise HTTPException(404, "报告不存在")
    data = json.loads(report.data_json or "{}")
    # Generate markdown from chapters for backward compat
    if "chapters" in data and "markdown" not in data:
        data["markdown"] = _chapters_to_markdown(data)
    return {
        "id": report.id,
        "report_key": report.report_key,
        "title": report.title,
        "summary": report.summary,
        "data": data,
        "created_at": str(report.created_at),
        "updated_at": str(report.updated_at),
    }


@router.delete("/{report_id}")
def delete_report(
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a report by ID (only if owned by user)."""
    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.user_id == user.id)
        .first()
    )
    if not report:
        raise HTTPException(404, "报告不存在")
    db.delete(report)
    db.commit()
    return {"ok": True}


class ReportEditBody(BaseModel):
    """Body for PATCH edit — partial update to narrative / chapter texts."""
    narrative_summary: str | None = None
    chapter_narratives: dict[str, str] | None = None  # {"ability": "...", ...}


@router.patch("/{report_id}")
def edit_report(
    report_id: int,
    body: ReportEditBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save user edits to a report's narrative texts."""
    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.user_id == user.id)
        .first()
    )
    if not report:
        raise HTTPException(404, "报告不存在")

    data = json.loads(report.data_json or "{}")
    narrative = data.setdefault("narrative", {})

    if body.narrative_summary is not None:
        narrative["summary"] = body.narrative_summary
        data["summary"] = body.narrative_summary
        report.summary = body.narrative_summary[:500]

    if body.chapter_narratives:
        ch_narr = narrative.setdefault("chapters", {})
        for key, text in body.chapter_narratives.items():
            ch_narr[key] = text

    data["user_edited"] = True
    report.data_json = json.dumps(data, ensure_ascii=False, default=str)
    db.commit()
    return {"ok": True}


@router.post("/{report_id}/polish")
def polish_report(
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Use LLM to polish the report narrative — improve readability and coherence."""
    from backend.llm import get_model, llm_chat, parse_json_response

    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.user_id == user.id)
        .first()
    )
    if not report:
        raise HTTPException(404, "报告不存在")

    data = json.loads(report.data_json or "{}")
    narrative = data.get("narrative", {})
    summary = narrative.get("summary", data.get("summary", ""))
    chapters = narrative.get("chapters", {})

    if not summary and not chapters:
        raise HTTPException(400, "报告无可润色内容")

    # Build polish prompt
    input_texts = {"summary": summary}
    input_texts.update(chapters)

    prompt = f"""你是一位专业的职业发展报告编辑。请润色以下报告文本，使其更流畅、专业、有洞察力。

要求：
- 保持原意不变，不要编造新事实
- 改善语句流畅度和专业度
- 每段控制在 80-150 字
- 使用第二人称（"你"）

原始文本：
{json.dumps(input_texts, ensure_ascii=False, indent=2)}

返回严格 JSON，格式与输入一致：
{{"summary": "润色后的总结", "ability": "润色后的能力洞察", ...}}

只返回 JSON，不要有任何其他文字。"""

    try:
        result = llm_chat(
            [{"role": "user", "content": prompt}],
            model=get_model("default"),
            temperature=0.5,
            timeout=60,
        )
        polished = parse_json_response(result)
    except Exception as e:
        logger.warning("Polish LLM failed: %s", e)
        raise HTTPException(500, "润色失败，请稍后重试")

    # Apply polished texts
    if not isinstance(polished, dict):
        raise HTTPException(500, "润色结果格式异常")

    if "summary" in polished:
        narrative["summary"] = polished["summary"]
        data["summary"] = polished["summary"]
        report.summary = polished["summary"][:500]

    ch_narr = narrative.setdefault("chapters", {})
    for key in ("ability", "job_match", "career_path", "action_plan", "interview"):
        if key in polished:
            ch_narr[key] = polished[key]

    data["narrative"] = narrative
    data["polished"] = True
    report.data_json = json.dumps(data, ensure_ascii=False, default=str)
    db.commit()

    return {"ok": True, "polished": polished}


_LEVEL_ZH = {
    "advanced": "精通",
    "proficient": "精通",
    "intermediate": "熟练",
    "beginner": "入门",
}


def _chapters_to_markdown(data: dict) -> str:
    """Convert structured chapters to readable markdown (fallback renderer)."""
    lines: list[str] = []
    # No title — page header already shows it

    summary = data.get("summary", "")
    if summary:
        lines.append(f"{summary}\n")

    for ch in data.get("chapters", []):
        if not ch.get("has_data", False):
            continue
        lines.append(f"## {ch.get('title', '')}")
        if ch.get("subtitle"):
            lines.append(f"*{ch['subtitle']}*\n")

        ch_data = ch.get("data", {})
        key = ch.get("key", "")

        if key == "ability":
            if ch_data.get("current_title"):
                lines.append(f"**当前职位:** {ch_data['current_title']}")
            if ch_data.get("major"):
                lines.append(f"**专业:** {ch_data['major']}")
            skills = ch_data.get("skills", [])
            if skills:
                lines.append(f"\n**技能（{len(skills)} 项）:**")
                for s in skills:
                    name = s.get("name", "")
                    level = _LEVEL_ZH.get(s.get("level", ""), s.get("level", ""))
                    lines.append(f"- {name}（{level}）")

        elif key == "job_match":
            lines.append(f"**目标岗位:** {ch_data.get('jd_title', '')}")
            lines.append(f"**匹配度:** {ch_data.get('match_score', 0)}%\n")
            matched = ch_data.get("matched_skills", [])
            if matched:
                lines.append("**匹配技能:**")
                for s in matched:
                    lines.append(f"- {s}")
            missing = ch_data.get("missing_skills", [])
            if missing:
                lines.append("\n**缺失技能:**")
                for s in missing:
                    skill_name = s.get("skill", s) if isinstance(s, dict) else str(s)
                    lines.append(f"- {skill_name}")
            verdict = ch_data.get("verdict", "")
            if verdict:
                lines.append(f"\n{verdict}")

        elif key == "career_path":
            goal = ch_data.get("goal")
            if goal:
                lines.append(f"**目标:** {goal.get('target_label', '')}")
                lines.append(f"**预计时间:** {goal.get('total_hours', 0)} 小时")
                gaps = goal.get("gap_skills", [])
                if gaps:
                    lines.append("\n**需补技能:**")
                    for g in gaps:
                        name = g.get("name", g) if isinstance(g, dict) else str(g)
                        lines.append(f"- {name}")
            routes = ch_data.get("escape_routes", [])
            if routes:
                lines.append("\n**可选路径:**")
                for r in routes:
                    lines.append(f"- {r.get('target_label', '')}")

        elif key == "action_plan":
            short = ch_data.get("short_term", [])
            if short:
                lines.append("\n### 短期重点")
                for a in short:
                    lines.append(f"- **{a.get('skill', '')}** — {a.get('detail', '')}")
            mid = ch_data.get("mid_term", [])
            if mid:
                lines.append("\n### 中期提升")
                for a in mid:
                    lines.append(f"- **{a.get('skill', '')}** — {a.get('detail', '')}")
            ck = ch_data.get("checklist")
            if ck:
                lines.append(f"\n**面试清单进度:** {ck.get('progress', 0)}%（{ck.get('passed', 0)}/{ck.get('total', 0)}）")

        elif key == "interview":
            total = ch_data.get("total_count", 0)
            avg = ch_data.get("avg_score", 0)
            lines.append(f"**复盘次数:** {total}")
            lines.append(f"**平均得分:** {avg} 分\n")
            records = ch_data.get("records", [])
            if records:
                lines.append("**近期记录:**")
                for r in records[:5]:
                    q = r.get("question", "")[:60]
                    s = r.get("score", 0)
                    lines.append(f"- {q}… ({s} 分)")

        else:
            for k, v in ch_data.items():
                if isinstance(v, str) and v:
                    lines.append(f"**{k}:** {v}")
                elif isinstance(v, list) and v:
                    lines.append(f"\n**{k}:**")
                    for item in v[:10]:
                        lines.append(f"- {item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)}")

        lines.append("")

    return "\n".join(lines)
