"""User-related ORM models."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    reports: Mapped[list["Report"]] = relationship(
        "Report", back_populates="owner", cascade="all, delete-orphan"
    )
    profiles: Mapped[list["Profile"]] = relationship(
        "Profile", back_populates="owner", cascade="all, delete-orphan"
    )


class UserNotification(Base):
    """主动推送消息。由 heartbeat scheduler 生成，前端轮询拉取。"""

    __tablename__ = "user_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # 'jd_followup' | 'inactive_nudge' | 'milestone_due' | 'tracked_company_update' | 'coach_intervention'
    trigger_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default=""
    )  # 'profile_ready' | 'recommendations_ready' | 'jd_diagnosis_complete' | 'stage_changed'
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    body: Mapped[str] = mapped_column(String(500), nullable=False)
    cta_label: Mapped[str | None] = mapped_column(String(32), nullable=True)  # "去投递" / "去更新"
    cta_route: Mapped[str | None] = mapped_column(String(128), nullable=True)  # "/growth-log" 等
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
