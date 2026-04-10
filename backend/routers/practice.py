"""Practice router — interview practice: analyze answers, get questions."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import get_db
from backend.db_models import InterviewQuestion, InterviewReview, JDDiagnosis, Profile, User
from backend.services.practice_service import PracticeService

router = APIRouter()
_practice_svc = PracticeService()


class AnalyzeRequest(BaseModel):
    question: str
    answer: str
    target_job: str = ""
    profile_id: int | None = None


@router.post("/analyze")
def analyze_answer(
    req: AnalyzeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit question + answer for AI scoring."""
    profile_summary = ""
    has_jd = False
    if req.profile_id:
        profile = (
            db.query(Profile)
            .filter(Profile.id == req.profile_id, Profile.user_id == user.id)
            .first()
        )
        if not profile:
            raise HTTPException(404, "画像不存在")
        data = json.loads(profile.profile_json or "{}")
        skills = data.get("skills", [])
        skill_names = [
            s.get("name", "") if isinstance(s, dict) else str(s)
            for s in skills
        ]
        profile_summary = f"技能: {', '.join(skill_names[:15])}"
        has_jd = (
            db.query(JDDiagnosis.id)
            .filter(JDDiagnosis.profile_id == req.profile_id)
            .first()
        ) is not None

    result = _practice_svc.analyze_answer(
        question=req.question,
        answer=req.answer,
        target_job=req.target_job,
        profile_summary=profile_summary,
        has_jd=has_jd,
    )

    # Persist review
    if req.profile_id:
        review = InterviewReview(
            profile_id=req.profile_id,
            target_job=req.target_job,
            question_text=req.question,
            answer_text=req.answer,
            analysis_json=json.dumps(result, ensure_ascii=False, default=str),
        )
        db.add(review)
        db.commit()

    return result


@router.get("/history")
def list_reviews(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List past practice reviews for the current user."""
    rows = (
        db.query(InterviewReview)
        .join(Profile, InterviewReview.profile_id == Profile.id)
        .filter(Profile.user_id == user.id)
        .order_by(InterviewReview.created_at.desc())
        .limit(50)
        .all()
    )
    results = []
    for r in rows:
        analysis = json.loads(r.analysis_json or "{}")
        score = analysis.get("score", 0)
        results.append(
            {
                "id": r.id,
                "profile_id": r.profile_id,
                "target_job": r.target_job,
                "question_text": r.question_text,
                "score": score,
                "created_at": str(r.created_at),
            }
        )
    return results


@router.delete("/reviews/{review_id}")
def delete_review(
    review_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a practice review by ID (only if owned by user)."""
    row = (
        db.query(InterviewReview)
        .join(Profile, InterviewReview.profile_id == Profile.id)
        .filter(InterviewReview.id == review_id, Profile.user_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(404, "记录不存在")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/questions")
def get_questions(
    skill_tag: str = Query("", description="技能标签筛选"),
    node_id: str = Query("", description="节点 ID 筛选"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get practice questions filtered by skill tag or node_id."""
    query = db.query(InterviewQuestion)
    if skill_tag:
        query = query.filter(InterviewQuestion.skill_tag.ilike(f"%{skill_tag}%"))
    if node_id:
        query = query.filter(InterviewQuestion.node_id == node_id)
    rows = query.order_by(InterviewQuestion.created_at.desc()).limit(20).all()
    return [
        {
            "id": q.id,
            "question": q.question,
            "skill_tag": q.skill_tag,
            "question_type": q.question_type,
            "question_category": q.question_category,
            "difficulty": q.difficulty,
            "answer_key": q.answer_key,
        }
        for q in rows
    ]
