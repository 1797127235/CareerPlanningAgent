"""Report router — career development report CRUD + generation + polish."""
from __future__ import annotations

import json
import logging
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response

logger = logging.getLogger(__name__)
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from backend.auth import get_current_user
from backend.db import get_db
from backend.db_models import ActionPlanV2, ActionProgress, Profile, Report, User

router = APIRouter()

import threading

# In-memory tracker of user_ids with an in-flight /generate request.
# Single-process uvicorn only; if we go multi-worker later, swap for Redis.
_generating_users: set[int] = set()
_generating_lock = threading.Lock()


# ── Schemas ────────────────────────────────────────────────────────────────────

class ReportListItem(BaseModel):
    id: int
    report_key: str
    title: str
    summary: str
    created_at: str
    profile_id: int | None = None


class ReportDetail(BaseModel):
    id: int
    report_key: str
    title: str
    summary: str
    data: dict[str, Any]
    created_at: str
    updated_at: str


class EditReportBody(BaseModel):
    narrative_summary: str | None = None
    chapter_narratives: dict[str, str] | None = None


class CheckBody(BaseModel):
    item_id: str
    done: bool


# ── Helpers ────────────────────────────────────────────────────────────────────

def _to_list_item(r: Report) -> dict:
    data = _parse_data(r.data_json)
    return {
        "id": r.id,
        "report_key": r.report_key,
        "title": r.title or "职业发展报告",
        "summary": r.summary or "",
        "created_at": r.created_at.isoformat() if r.created_at else "",
        "profile_id": data.get("student", {}).get("profile_id"),
        "match_score": data.get("match_score"),
    }


def _to_detail(r: Report) -> dict:
    return {
        "id": r.id,
        "report_key": r.report_key,
        "title": r.title or "职业发展报告",
        "summary": r.summary or "",
        "data": _parse_data(r.data_json),
        "created_at": r.created_at.isoformat() if r.created_at else "",
        "updated_at": r.updated_at.isoformat() if r.updated_at else "",
    }


def _parse_data(data_json: str) -> dict:
    try:
        return json.loads(data_json or "{}")
    except Exception:
        return {}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/generate")
def generate_report(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate and persist a new career development report for the current user."""
    from backend.services.report import generate_report as _generate

    with _generating_lock:
        _generating_users.add(user.id)

    try:
        try:
            data = _generate(user_id=user.id, db=db)
        except ValueError as e:
            msg = str(e)
            if "no_profile" in msg:
                raise HTTPException(400, "请先上传简历完成能力画像")
            if "no_goal" in msg:
                raise HTTPException(400, "请先在岗位图谱中设定职业目标")
            print(f"[report/generate] ValueError for user {user.id}: {msg}")
            traceback.print_exc()
            raise HTTPException(400, f"报告生成失败：{msg}")
        except Exception as e:
            print(f"[report/generate] Exception for user {user.id}: {type(e).__name__}: {e}")
            traceback.print_exc()
            raise HTTPException(500, f"报告生成异常：{e}")

        target_label = data.get("target", {}).get("label", "职业发展报告")
        match_score = data.get("match_score", 0)
        narrative = data.get("narrative", "")
        summary_text = narrative[:80] + "…" if len(narrative) > 80 else narrative

        report_key_str = str(uuid.uuid4())

        report = Report(
            report_key=report_key_str,
            user_id=user.id,
            title=f"{target_label} — 职业发展报告",
            summary=summary_text,
            data_json=json.dumps(data, ensure_ascii=False),
        )
        db.add(report)

        # Write staged action plan to ActionPlanV2
        action_plan = data.get("action_plan", {})
        profile_id = data.get("student", {}).get("profile_id")
        if profile_id:
            for stage_data in action_plan.get("stages", []):
                plan_row = ActionPlanV2(
                    profile_id=profile_id,
                    report_key=report_key_str,
                    stage=stage_data["stage"],
                    status="ready",
                    content=stage_data,
                    time_budget={"duration": stage_data["duration"]},
                    generated_at=datetime.now(timezone.utc),
                )
                db.add(plan_row)

        db.commit()
        db.refresh(report)

        return _to_detail(report)
    finally:
        with _generating_lock:
            _generating_users.discard(user.id)


@router.get("/status")
def report_generation_status(
    user: User = Depends(get_current_user),
):
    """Is there an in-flight /generate for this user?

    Used by the frontend to recover the 'generating' UI after a page navigation.
    In-memory only; restarts clear it.
    """
    with _generating_lock:
        is_generating = user.id in _generating_users
    return {"generating": is_generating}


@router.get("/")
def list_reports(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all reports for the current user (newest first)."""
    reports = (
        db.query(Report)
        .filter(Report.user_id == user.id)
        .order_by(Report.created_at.desc())
        .limit(20)
        .all()
    )
    return [_to_list_item(r) for r in reports]


@router.get("/{report_id}")
def get_report(
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return a single report by ID."""
    report = db.query(Report).filter(
        Report.id == report_id,
        Report.user_id == user.id,
    ).first()
    if not report:
        raise HTTPException(404, "报告不存在")
    return _to_detail(report)


@router.patch("/{report_id}")
def edit_report(
    report_id: int,
    body: EditReportBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually edit narrative or chapter text in a report."""
    report = db.query(Report).filter(
        Report.id == report_id,
        Report.user_id == user.id,
    ).first()
    if not report:
        raise HTTPException(404, "报告不存在")

    data = _parse_data(report.data_json)

    if body.narrative_summary is not None:
        data["narrative"] = body.narrative_summary
        report.summary = (
            body.narrative_summary[:80] + "…"
            if len(body.narrative_summary) > 80
            else body.narrative_summary
        )

    if body.chapter_narratives:
        data.setdefault("chapter_narratives", {}).update(body.chapter_narratives)

    report.data_json = json.dumps(data, ensure_ascii=False)
    db.commit()
    return {"ok": True}


@router.post("/{report_id}/polish")
def polish_report(
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Use LLM to polish the narrative of an existing report."""
    from backend.services.report import polish_narrative

    report = db.query(Report).filter(
        Report.id == report_id,
        Report.user_id == user.id,
    ).first()
    if not report:
        raise HTTPException(404, "报告不存在")

    data = _parse_data(report.data_json)
    old_narrative = data.get("narrative", "")
    target_label = data.get("target", {}).get("label", "目标岗位")

    polished = polish_narrative(old_narrative, target_label)
    data["narrative"] = polished
    report.data_json = json.dumps(data, ensure_ascii=False)
    report.summary = polished[:80] + "…" if len(polished) > 80 else polished
    db.commit()

    return {"ok": True, "polished": {"narrative": polished}}


@router.post("/{report_id}/export")
async def export_report_pdf(
    report_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export a report as PDF via Playwright headless rendering."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")
    if report.user_id != user.id:
        raise HTTPException(403, "Not authorized")

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    token = auth[len("Bearer "):]

    user_json = {
        "id": user.id,
        "username": user.username,
    }

    from backend.services.report.pdf_export import render_report_pdf
    try:
        pdf_bytes = await render_report_pdf(report_id, token, user_json)
    except Exception as e:
        logger.exception("PDF export failed")
        raise HTTPException(500, f"PDF 生成失败：{e}")

    report_data = _parse_data(report.data_json)
    target = report_data.get("target", {}).get("label", "报告") if isinstance(report_data, dict) else "报告"
    date_str = report.created_at.strftime("%Y-%m-%d") if report.created_at else "unknown"
    filename = f"{target}_职业报告_{date_str}.pdf"
    from urllib.parse import quote
    encoded = quote(filename)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded}",
        },
    )


@router.delete("/{report_id}")
def delete_report(
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a report."""
    report = db.query(Report).filter(
        Report.id == report_id,
        Report.user_id == user.id,
    ).first()
    if not report:
        raise HTTPException(404, "报告不存在")
    db.delete(report)
    db.commit()
    return {"ok": True}


# ── Plan endpoints ───────────────────────────────────────────────────────────


@router.get("/{report_id}/plan")
def get_plan(
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get staged action plan for a report."""
    report = db.query(Report).filter(
        Report.id == report_id,
        Report.user_id == user.id,
    ).first()
    if not report:
        raise HTTPException(404, "报告不存在")

    data = _parse_data(report.data_json)
    profile_id = data.get("student", {}).get("profile_id")

    stages_query = db.query(ActionPlanV2).filter(
        ActionPlanV2.report_key == report.report_key,
    )
    if profile_id:
        stages_query = stages_query.filter(ActionPlanV2.profile_id == profile_id)
    stages = stages_query.order_by(ActionPlanV2.stage).all()

    # Also get checked state
    progress_query = db.query(ActionProgress).filter(
        ActionProgress.report_key == report.report_key,
    )
    if profile_id:
        progress_query = progress_query.filter(ActionProgress.profile_id == profile_id)
    progress = progress_query.first()
    checked = progress.checked if progress else {}

    return {
        "stages": [
            s.content if isinstance(s.content, dict) else json.loads(s.content or "{}")
            for s in stages
        ],
        "checked": checked,
    }


@router.patch("/{report_id}/plan/check")
def update_plan_check(
    report_id: int,
    body: CheckBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Toggle task check status."""
    report = db.query(Report).filter(
        Report.id == report_id,
        Report.user_id == user.id,
    ).first()
    if not report:
        raise HTTPException(404, "报告不存在")

    data = _parse_data(report.data_json)
    profile_id = data.get("student", {}).get("profile_id")
    if not profile_id:
        raise HTTPException(400, "报告缺少 profile_id")

    progress = db.query(ActionProgress).filter(
        ActionProgress.profile_id == profile_id,
        ActionProgress.report_key == report.report_key,
    ).first()
    if not progress:
        progress = ActionProgress(
            profile_id=profile_id,
            report_key=report.report_key,
            checked={},
        )
        db.add(progress)
        db.flush()

    progress.checked[body.item_id] = body.done
    flag_modified(progress, "checked")
    db.commit()
    return {"ok": True}
