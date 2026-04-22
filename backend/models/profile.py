"""Profile and career goal ORM models."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    profile_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    quality_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    source: Mapped[str] = mapped_column(
        String(32), nullable=False, default="resume"
    )  # 'resume' or 'manual'
    cached_recs_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="{}"
    )  # {"hash": "...", "data": {"recommendations": [...], "user_skill_count": N}}
    cached_gaps_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="{}"
    )  # {"hash": "...", "roles": {"role_id": {gap_result}, ...}}
    coach_memo: Mapped[str] = mapped_column(
        Text, nullable=False, default=""
    )  # Natural-language coach memo about user, updated across sessions
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    owner: Mapped["User"] = relationship("User", back_populates="profiles")


class SjtSession(Base):
    """Temporary storage for generated SJT questions between generate and submit."""

    __tablename__ = "sjt_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("profiles.id"), nullable=False, index=True
    )
    questions_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CareerGoal(Base):
    """用户目标方向 — 从岗位图谱逃生路线设定"""

    __tablename__ = "career_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("profiles.id"), nullable=False, index=True
    )

    # 目标节点
    target_node_id: Mapped[str] = mapped_column(String(128), nullable=False)
    target_label: Mapped[str] = mapped_column(String(128), nullable=False)
    target_zone: Mapped[str] = mapped_column(String(16), nullable=False, default="safe")

    # 逃生路线快照（设定时冻结）
    gap_skills: Mapped[list] = mapped_column(JSON, default=list)
    total_hours: Mapped[int] = mapped_column(Integer, default=0)
    safety_gain: Mapped[float] = mapped_column(Float, default=0.0)
    salary_p50: Mapped[int] = mapped_column(Integer, default=0)
    tag: Mapped[str] = mapped_column(String(16), default="")
    transition_probability: Mapped[float] = mapped_column(Float, default=0.0)

    # 来源
    from_node_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")

    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    set_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
