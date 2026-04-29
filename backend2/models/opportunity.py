"""backend2/models/opportunity.py — 职位机会评估 v2 ORM。"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JDDiagnosisV2(Base):
    __tablename__ = "jd_diagnoses_v2"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("profiles.id"), nullable=False
    )
    profile_parse_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("profile_parses.id"), nullable=True
    )

    jd_text: Mapped[str] = mapped_column(Text, nullable=False)
    jd_title: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    company: Mapped[str] = mapped_column(String(128), nullable=False, default="")

    profile_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    jd_extract_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    result_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    match_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
