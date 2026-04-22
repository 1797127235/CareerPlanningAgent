"""Mock interview and question bank ORM models."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MockInterview(Base):
    """AI 模拟面试会话"""
    __tablename__ = "mock_interviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    target_role: Mapped[str] = mapped_column(String(256), nullable=False)
    jd_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    questions_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    answers_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluation_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class InterviewQuestionBank(Base):
    """预生成面试题库 — 各方向高质量题目缓存"""

    __tablename__ = "interview_question_bank"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    focus_area: Mapped[str] = mapped_column(String(200), nullable=False)
    follow_ups: Mapped[str] = mapped_column(Text, default="[]")
    topic_summary: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    generated_by: Mapped[str] = mapped_column(String(20), default="llm")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
