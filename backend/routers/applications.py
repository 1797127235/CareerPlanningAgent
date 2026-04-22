"""Applications router — job application tracking + interview debrief."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import get_db
from backend.models import (
    InterviewDebrief,
    JDDiagnosis,
    JobApplication,
    Profile,
    User,
)
from backend.services.debrief_service import DebriefService

router = APIRouter()
_debrief_svc = DebriefService()


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class CreateApplicationRequest(BaseModel):
    jd_diagnosis_id: Optional[int] = None
    company: Optional[str] = None
    position: Optional[str] = None
    job_url: Optional[str] = None
    notes: Optional[str] = None


class UpdateStatusRequest(BaseModel):
    status: str  # applied|screening|scheduled|interviewed|debriefed|offer|rejected|withdrawn


class SetInterviewTimeRequest(BaseModel):
    interview_at: str  # ISO 8601 string


class UpdateNotesRequest(BaseModel):
    notes: str


class QAItem(BaseModel):
    question: str
    answer: str


class SubmitDebriefRequest(BaseModel):
    qa_list: list[QAItem]


# ── Helper ────────────────────────────────────────────────────────────────────

VALID_STATUSES = {
    "pending", "applied", "screening", "scheduled",
    "interviewed", "debriefed", "offer", "rejected", "withdrawn",
}


def _app_to_dict(
    app: JobApplication,
    debrief: InterviewDebrief | None = None,
    jd_title: str | None = None,
    jd_diagnosis: JDDiagnosis | None = None,
) -> dict:
    d: dict = {
        "id": app.id,
        "jd_diagnosis_id": app.jd_diagnosis_id,
        "jd_title": jd_title,
        "company": app.company,
        "position": app.position,
        "job_url": app.job_url,
        "status": app.status,
        "applied_at": app.applied_at.isoformat() if app.applied_at else None,
        "interview_at": app.interview_at.isoformat() if app.interview_at else None,
        "completed_at": app.completed_at.isoformat() if app.completed_at else None,
        "notes": app.notes,
        "reflection": app.reflection,
        "reminder_sent": app.reminder_sent,
        "created_at": app.created_at.isoformat(),
        "updated_at": app.updated_at.isoformat(),
        "debrief": None,
        "jd_diagnosis": None,
    }
    if debrief:
        d["debrief"] = {
            "id": debrief.id,
            "raw_input": json.loads(debrief.raw_input or "[]"),
            "report": json.loads(debrief.report_json) if debrief.report_json else None,
            "created_at": debrief.created_at.isoformat(),
        }
    if jd_diagnosis:
        result = json.loads(jd_diagnosis.result_json or "{}")
        d["jd_diagnosis"] = {
            "match_score": jd_diagnosis.match_score,
            "gap_skills": result.get("gap_skills", []),
            "matched_skills": result.get("matched_skills", []),
        }
    return d


def _get_jd_title(db: Session, jd_id: int | None) -> str | None:
    if not jd_id:
        return None
    jd = db.query(JDDiagnosis.jd_title).filter(JDDiagnosis.id == jd_id).first()
    return jd[0] if jd else None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("")
def list_applications(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all job applications for the current user, newest first."""
    apps = (
        db.query(JobApplication)
        .filter(JobApplication.user_id == user.id)
        .order_by(JobApplication.updated_at.desc())
        .all()
    )
    result = []
    for app in apps:
        debrief = (
            db.query(InterviewDebrief)
            .filter(InterviewDebrief.application_id == app.id)
            .order_by(InterviewDebrief.created_at.desc())
            .first()
        )
        jd = db.query(JDDiagnosis).filter(JDDiagnosis.id == app.jd_diagnosis_id).first() if app.jd_diagnosis_id else None
        result.append(_app_to_dict(app, debrief, jd.jd_title if jd else None, jd))
    return result


@router.post("")
def create_application(
    req: CreateApplicationRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new job application record."""
    # Validate jd_diagnosis ownership if provided
    if req.jd_diagnosis_id:
        jd = db.query(JDDiagnosis).filter(
            JDDiagnosis.id == req.jd_diagnosis_id,
            JDDiagnosis.user_id == user.id,
        ).first()
        if not jd:
            raise HTTPException(404, "JD 诊断记录不存在")

        # Prevent duplicate: one application per JD diagnosis
        existing = db.query(JobApplication).filter(
            JobApplication.user_id == user.id,
            JobApplication.jd_diagnosis_id == req.jd_diagnosis_id,
        ).first()
        if existing:
            debrief = db.query(InterviewDebrief).filter(
                InterviewDebrief.application_id == existing.id
            ).order_by(InterviewDebrief.created_at.desc()).first()
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "already_exists",
                    "application": _app_to_dict(existing, debrief, jd.jd_title),
                },
            )

    # Auto-populate position from JD title if not provided
    position = req.position
    if not position and req.jd_diagnosis_id:
        jd = db.query(JDDiagnosis).filter(JDDiagnosis.id == req.jd_diagnosis_id).first()
        if jd:
            position = jd.jd_title

    app = JobApplication(
        user_id=user.id,
        jd_diagnosis_id=req.jd_diagnosis_id,
        company=req.company,
        position=position,
        job_url=req.job_url,
        notes=req.notes,
        status="applied",
        applied_at=datetime.now(timezone.utc),
    )
    db.add(app)
    db.commit()
    db.refresh(app)

    # Auto-complete matching action plan tasks
    try:
        from backend.routers.growth_log import _auto_complete_plan_tasks
        _auto_complete_plan_tasks(db, user.id, record_type="application")
    except Exception:
        pass  # non-critical

    return _app_to_dict(app, None, _get_jd_title(db, app.jd_diagnosis_id))


@router.get("/{app_id}")
def get_application(
    app_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single application with its debrief (if any)."""
    app = db.query(JobApplication).filter(
        JobApplication.id == app_id, JobApplication.user_id == user.id
    ).first()
    if not app:
        raise HTTPException(404, "投递记录不存在")
    debrief = (
        db.query(InterviewDebrief)
        .filter(InterviewDebrief.application_id == app_id)
        .order_by(InterviewDebrief.created_at.desc())
        .first()
    )
    jd = db.query(JDDiagnosis).filter(JDDiagnosis.id == app.jd_diagnosis_id).first() if app.jd_diagnosis_id else None
    return _app_to_dict(app, debrief, jd.jd_title if jd else None, jd)


@router.patch("/{app_id}/status")
def update_status(
    app_id: int,
    req: UpdateStatusRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update application status."""
    if req.status not in VALID_STATUSES:
        raise HTTPException(400, f"无效状态: {req.status}")
    app = db.query(JobApplication).filter(
        JobApplication.id == app_id, JobApplication.user_id == user.id
    ).first()
    if not app:
        raise HTTPException(404, "投递记录不存在")
    app.status = req.status
    if req.status == "interviewed" and not app.completed_at:
        app.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(app)
    return _app_to_dict(app, None, _get_jd_title(db, app.jd_diagnosis_id))


@router.patch("/{app_id}/interview-time")
def set_interview_time(
    app_id: int,
    req: SetInterviewTimeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set or update the scheduled interview time."""
    app = db.query(JobApplication).filter(
        JobApplication.id == app_id, JobApplication.user_id == user.id
    ).first()
    if not app:
        raise HTTPException(404, "投递记录不存在")
    try:
        dt = datetime.fromisoformat(req.interview_at.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(400, "时间格式无效，请使用 ISO 8601")
    app.interview_at = dt
    app.reminder_sent = False  # Reset so reminder fires again if time changes
    if app.status in ("applied", "screening"):
        app.status = "scheduled"
    db.commit()
    db.refresh(app)
    return _app_to_dict(app, None, _get_jd_title(db, app.jd_diagnosis_id))


@router.patch("/{app_id}/notes")
def update_notes(
    app_id: int,
    req: UpdateNotesRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update notes for an application."""
    app = db.query(JobApplication).filter(
        JobApplication.id == app_id, JobApplication.user_id == user.id
    ).first()
    if not app:
        raise HTTPException(404, "投递记录不存在")
    app.notes = req.notes[:2000]
    db.commit()
    return {"success": True}


@router.patch("/{app_id}/reflection")
def update_reflection(
    app_id: int,
    req: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update reflection for an application."""
    app = db.query(JobApplication).filter(
        JobApplication.id == app_id, JobApplication.user_id == user.id
    ).first()
    if not app:
        raise HTTPException(404, "投递记录不存在")
    app.reflection = (req.get("reflection") or "")[:5000] or None
    db.commit()
    return {"success": True}


@router.delete("/{app_id}")
def delete_application(
    app_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an application and its debriefs."""
    app = db.query(JobApplication).filter(
        JobApplication.id == app_id, JobApplication.user_id == user.id
    ).first()
    if not app:
        raise HTTPException(404, "投递记录不存在")
    # 级联删除：关联面试记录 + debrief
    from backend.models import InterviewRecord as IR
    db.query(IR).filter(IR.application_id == app_id).delete()
    db.query(InterviewDebrief).filter(InterviewDebrief.application_id == app_id).delete()
    db.delete(app)
    db.commit()
    return {"success": True}


@router.post("/{app_id}/debrief")
def submit_debrief(
    app_id: int,
    req: SubmitDebriefRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit QA list for LLM debrief analysis."""
    app = db.query(JobApplication).filter(
        JobApplication.id == app_id, JobApplication.user_id == user.id
    ).first()
    if not app:
        raise HTTPException(404, "投递记录不存在")
    if not req.qa_list:
        raise HTTPException(400, "至少需要一道题目")

    # Fetch JD context
    jd_text = ""
    profile_data: dict = {}
    if app.jd_diagnosis_id:
        jd_row = db.query(JDDiagnosis).filter(JDDiagnosis.id == app.jd_diagnosis_id).first()
        if jd_row:
            jd_text = jd_row.jd_text or ""
            # Fetch linked profile
            p = db.query(Profile).filter(Profile.id == jd_row.profile_id).first()
            if p:
                profile_data = json.loads(p.profile_json or "{}")

    qa_dicts = [{"question": item.question, "answer": item.answer} for item in req.qa_list]

    # Run LLM analysis
    report = _debrief_svc.analyze(qa_dicts, jd_text=jd_text, profile_data=profile_data)

    # Persist
    debrief = InterviewDebrief(
        user_id=user.id,
        application_id=app_id,
        raw_input=json.dumps(qa_dicts, ensure_ascii=False),
        report_json=json.dumps(report, ensure_ascii=False),
    )
    db.add(debrief)

    # Auto-advance status to debriefed
    if app.status == "interviewed":
        app.status = "debriefed"

    db.commit()
    db.refresh(debrief)

    return {
        "id": debrief.id,
        "raw_input": qa_dicts,
        "report": report,
        "created_at": debrief.created_at.isoformat(),
    }
