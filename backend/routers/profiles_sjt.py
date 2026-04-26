"""SJT (soft-skill judgement test) routes for profiles.

POST /sjt/generate — create assessment session
GET  /sjt/progress — resume in-progress session
POST /sjt/save     — save partial progress
POST /sjt/submit   — score answers and write results back
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import get_db
from backend.models import SjtSession, User
from backend.routers._profiles_helpers import _get_or_create_profile, _load_profile_json
from backend.services.profile import ProfileService
from backend.services.profile.sjt import score_to_level
from backend.utils import ok

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/sjt/generate")
def generate_sjt(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate personalized SJT questions based on the user's profile.

    Deletes any previous in-progress session for this profile so that
    only one active session exists at a time.
    """
    profile = _get_or_create_profile(user.id, db)
    profile_data = _load_profile_json(profile)

    # Drop stale in-progress sessions for this profile
    db.query(SjtSession).filter(
        SjtSession.profile_id == profile.id,
        SjtSession.status == "in_progress",
    ).delete(synchronize_session=False)

    try:
        questions = ProfileService.generate_sjt_questions(profile_data)
    except Exception as e:
        raise HTTPException(500, f"生成失败，请重试: {e}")

    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    session = SjtSession(
        id=session_id,
        profile_id=profile.id,
        questions_json=json.dumps(questions, ensure_ascii=False, default=str),
        answers_json="[]",
        current_idx=0,
        status="in_progress",
        created_at=now,
    )
    db.add(session)
    db.commit()

    safe_questions = [
        {
            "id": q["id"],
            "dimension": q["dimension"],
            "scenario": q["scenario"],
            "options": [{"id": o["id"], "text": o["text"]} for o in q["options"]],
        }
        for q in questions
    ]
    return ok({"session_id": session_id, "questions": safe_questions})


@router.get("/sjt/progress")
def get_sjt_progress(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the user's in-progress SJT session (questions + saved answers)."""
    profile = _get_or_create_profile(user.id, db)

    session = (
        db.query(SjtSession)
        .filter(
            SjtSession.profile_id == profile.id,
            SjtSession.status == "in_progress",
        )
        .first()
    )

    if not session:
        return ok(None)

    questions = json.loads(session.questions_json)
    safe_questions = [
        {
            "id": q["id"],
            "dimension": q["dimension"],
            "scenario": q["scenario"],
            "options": [{"id": o["id"], "text": o["text"]} for o in q["options"]],
        }
        for q in questions
    ]

    return ok({
        "session_id": session.id,
        "questions": safe_questions,
        "answers": json.loads(session.answers_json) if session.answers_json else [],
        "current_idx": session.current_idx,
    })


class SjtSaveRequest(BaseModel):
    session_id: str
    answers: list[dict]
    current_idx: int


@router.post("/sjt/save")
def save_sjt_progress(
    req: SjtSaveRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save partial progress (answers + current question index)."""
    profile = _get_or_create_profile(user.id, db)

    session = db.query(SjtSession).filter(SjtSession.id == req.session_id).first()
    if not session:
        raise HTTPException(410, "评估会话不存在，请重新开始")
    if session.profile_id != profile.id:
        raise HTTPException(400, "会话与画像不匹配")
    if session.status != "in_progress":
        raise HTTPException(400, "评估已完成")

    session.answers_json = json.dumps(req.answers, ensure_ascii=False, default=str)
    session.current_idx = req.current_idx
    db.commit()

    return ok({"saved": True})


class SjtSubmitRequest(BaseModel):
    session_id: str
    answers: list[dict]


@router.post("/sjt/submit")
def submit_sjt(
    req: SjtSubmitRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Score SJT v2 answers, generate advice, write back to profile."""
    profile = _get_or_create_profile(user.id, db)

    session = db.query(SjtSession).filter(SjtSession.id == req.session_id).first()
    if not session:
        raise HTTPException(410, "评估会话不存在，请重新开始")
    if session.profile_id != profile.id:
        raise HTTPException(400, "会话与画像不匹配")

    questions = json.loads(session.questions_json)
    expected_ids = {q["id"] for q in questions}
    submitted_ids = {a.get("question_id") for a in req.answers}
    missing = expected_ids - submitted_ids
    if missing:
        raise HTTPException(400, f"缺少以下题目的回答: {', '.join(sorted(missing))}")

    result = ProfileService.score_sjt_v2(req.answers, questions)
    dimensions = result["dimensions"]

    profile_data = _load_profile_json(profile)
    advice = ProfileService.generate_sjt_advice(dimensions, req.answers, questions, profile_data)

    soft_skills = {"_version": 2}
    for dim, info in dimensions.items():
        soft_skills[dim] = {
            "score": info["score"],
            "level": info["level"],
            "advice": advice.get(dim, ""),
        }

    profile_data["soft_skills"] = soft_skills
    profile.profile_json = json.dumps(profile_data, ensure_ascii=False, default=str)
    quality_data = ProfileService.compute_quality(profile_data)
    profile.quality_json = json.dumps(quality_data, ensure_ascii=False, default=str)

    # Mark session completed instead of deleting it
    session.status = "completed"
    session.answers_json = json.dumps(req.answers, ensure_ascii=False, default=str)
    session.current_idx = len(questions)
    db.commit()

    all_scores = [info["score"] for info in dimensions.values()]
    overall_score = round(sum(all_scores) / len(all_scores)) if all_scores else 0
    overall_level = score_to_level(overall_score)

    return ok({
        "dimensions": [
            {"key": dim, "level": info["level"], "advice": advice.get(dim, "")}
            for dim, info in dimensions.items()
        ],
        "overall_level": overall_level,
    })
