"""Market signal models — unified role_family and city-level signals."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.db import Base


class MarketSignal(Base):
    """市场信号表：存储从招聘数据中提取的 role_family 级信号."""
    __tablename__ = "market_signals"
    __table_args__ = (
        UniqueConstraint("role_family", "batch_date", name="uq_family_batch"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_family: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    batch_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # 核心信号
    posting_count: Mapped[int] = mapped_column(Integer, default=0)
    salary_median: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_tool_mention_rate: Mapped[float] = mapped_column(Float, default=0.0)
    routine_task_rate: Mapped[float] = mapped_column(Float, default=0.0)
    creative_task_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # 趋势信号（与上一批次对比）
    salary_trend: Mapped[float | None] = mapped_column(Float, nullable=True)
    posting_trend: Mapped[float | None] = mapped_column(Float, nullable=True)

    # 新兴技能（JSON list）
    emerging_skills: Mapped[str | None] = mapped_column(Text, nullable=True)


class CityMarketSignal(Base):
    """城市级市场信号表：存储从招聘数据中提取的 (role_family, city) 级信号."""
    __tablename__ = "city_market_signals"
    __table_args__ = (
        UniqueConstraint("role_family", "city", "batch_date", name="uq_family_city_batch"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_family: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    batch_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # 核心信号
    posting_count: Mapped[int] = mapped_column(Integer, default=0)
    salary_median: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_tool_mention_rate: Mapped[float] = mapped_column(Float, default=0.0)
    routine_task_rate: Mapped[float] = mapped_column(Float, default=0.0)
    creative_task_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # 趋势信号（与上一批次对比）
    salary_trend: Mapped[float | None] = mapped_column(Float, nullable=True)
    posting_trend: Mapped[float | None] = mapped_column(Float, nullable=True)
