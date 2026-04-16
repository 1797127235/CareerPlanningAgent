"""SJT soft-skill assessment routes (v2)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import get_db
from backend.db_models import SjtSession, User
from backend.routers._profiles_helpers import _get_or_create_profile
from backend.services.profile import ProfileService
from backend.utils import ok

router = APIRouter()


@router.post("/sjt/generate")
def generate_sjt(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate personalized SJT questions based on the user's profile."""
    profile = _get_or_create_profile(user.id, db)
    profile_data = json.loads(profile.profile_json or "{}")

    try:
        questions = ProfileService.generate_sjt_questions(profile_data)
    except Exception:
        try:
            questions = ProfileService.generate_sjt_questions(profile_data)
        except Exception as e:
            raise HTTPException(500, f"生成失败，请重试: {e}")

    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    session = SjtSession(
        id=session_id,
        profile_id=profile.id,
        questions_json=json.dumps(questions, ensure_ascii=False),
        created_at=now,
        expires_at=now + timedelta(hours=1),
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

    now_utc = datetime.now(timezone.utc)
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now_utc:
        db.delete(session)
        db.commit()
        raise HTTPException(410, "评估已过期，请重新开始")

    questions = json.loads(session.questions_json)
    expected_ids = {q["id"] for q in questions}
    submitted_ids = {a.get("question_id") for a in req.answers}
    missing = expected_ids - submitted_ids
    if missing:
        raise HTTPException(400, f"缺少以下题目的回答: {', '.join(sorted(missing))}")

    result = ProfileService.score_sjt_v2(req.answers, questions)
    dimensions = result["dimensions"]

    profile_data = json.loads(profile.profile_json or "{}")
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

    db.delete(session)
    db.commit()

    all_scores = [info["score"] for info in dimensions.values()]
    overall_score = round(sum(all_scores) / len(all_scores)) if all_scores else 0
    overall_level = ProfileService.score_to_level(overall_score)

    return ok({
        "dimensions": [
            {"key": dim, "level": info["level"], "advice": advice.get(dim, "")}
            for dim, info in dimensions.items()
        ],
        "overall_level": overall_level,
    })
