"""Coach results router — store and retrieve structured agent outputs."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import get_db
from backend.models import CoachResult, User

router = APIRouter()


@router.get("/{result_id}")
def get_coach_result(
    result_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single coach result by ID."""
    result = (
        db.query(CoachResult)
        .filter(CoachResult.id == result_id, CoachResult.user_id == user.id)
        .first()
    )
    if not result:
        raise HTTPException(404, "结果不存在")

    detail = {}
    try:
        detail = json.loads(result.detail_json or "{}")
    except (json.JSONDecodeError, TypeError):
        pass

    metadata = {}
    try:
        metadata = json.loads(result.metadata_json or "{}")
    except (json.JSONDecodeError, TypeError):
        pass

    return {
        "id": result.id,
        "result_type": result.result_type,
        "title": result.title,
        "summary": result.summary,
        "detail": detail,
        "metadata": metadata,
        "created_at": str(result.created_at),
    }


@router.get("")
@router.get("/")
def list_coach_results(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all coach results for the current user."""
    results = (
        db.query(CoachResult)
        .filter(CoachResult.user_id == user.id)
        .order_by(CoachResult.created_at.desc())
        .limit(50)
        .all()
    )
    out = []
    for r in results:
        meta = {}
        try:
            meta = json.loads(r.metadata_json or "{}")
        except (json.JSONDecodeError, TypeError):
            pass
        out.append({
            "id": r.id,
            "result_type": r.result_type,
            "title": r.title,
            "summary": r.summary,
            "metadata": meta,
            "created_at": str(r.created_at),
        })
    return out


@router.delete("/{result_id}")
def delete_coach_result(
    result_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a coach result."""
    result = (
        db.query(CoachResult)
        .filter(CoachResult.id == result_id, CoachResult.user_id == user.id)
        .first()
    )
    if not result:
        raise HTTPException(404, "结果不存在")
    db.delete(result)
    db.commit()
    return {"message": "已删除"}
