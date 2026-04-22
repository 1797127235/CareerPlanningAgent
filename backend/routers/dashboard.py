"""Dashboard router — aggregate stats for user dashboard."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import get_db
from backend.models import Profile, User
from backend.services.dashboard_service import get_dashboard_stats, get_activity_heatmap

router = APIRouter()


@router.get("/stats")
def dashboard_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get dashboard stats (profile inferred from current user)."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(404, "请先上传简历建立画像")
    profile_id = profile.id

    stats = get_dashboard_stats(profile_id, db)
    return stats


@router.get("/activity-heatmap")
def activity_heatmap(
    weeks: int = Query(16, ge=4, le=52),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return daily activity counts for heatmap rendering."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(404, "请先上传简历建立画像")
    return get_activity_heatmap(profile.id, db, weeks)
