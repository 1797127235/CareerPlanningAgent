"""JD diagnosis and job application ORM models."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JDDiagnosis(Base):
    """JD匹配诊断记录"""

    __tablename__ = "jd_diagnoses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("profiles.id"), nullable=False, index=True
    )
    jd_text: Mapped[str] = mapped_column(Text, nullable=False)
    jd_title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    match_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class JobApplication(Base):
    """用户投递记录 — 状态机 + 面试时间 + 复盘关联"""

    __tablename__ = "job_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    jd_diagnosis_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("jd_diagnoses.id"), nullable=True)

    company: Mapped[str | None] = mapped_column(String(256), nullable=True)
    position: Mapped[str | None] = mapped_column(String(256), nullable=True)
    job_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # pending | applied | screening | scheduled | interviewed | debriefed | offer | rejected | withdrawn
    status: Mapped[str] = mapped_column(String(32), default="applied", nullable=False, index=True)

    applied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    interview_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reflection: Mapped[str | None] = mapped_column(Text, nullable=True)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class InterviewDebrief(Base):
    """面试复盘记录 — 题目+回答 → LLM 分析报告"""

    __tablename__ = "interview_debriefs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    application_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("job_applications.id"), nullable=True)

    raw_input: Mapped[str] = mapped_column(Text, nullable=False, default="[]")   # JSON: [{question, answer}, ...]
    report_json: Mapped[str | None] = mapped_column(Text, nullable=True)          # LLM 输出的复盘报告 JSON

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
