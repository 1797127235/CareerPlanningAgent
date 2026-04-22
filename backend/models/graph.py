"""Job graph and skill ORM models."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    aliases: Mapped[str] = mapped_column(Text, default="")
    # 技能级基准分（替代旧的 15 类别常量）
    replacement_pressure_base: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    leverage_base: Mapped[float | None] = mapped_column(Float, nullable=True)
    reasoning: Mapped[str] = mapped_column(Text, default="")


class AiToolMapping(Base):
    __tablename__ = "ai_tool_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_name: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    tools: Mapped[list] = mapped_column(JSON, default=list)


class JobNode(Base):
    __tablename__ = "job_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    role_family: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # 岗位基本信息
    salary_p50: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exp_years_median: Mapped[float | None] = mapped_column(Float, nullable=True)
    education_primary: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # 技能与任务（JSON 数组）
    must_skills: Mapped[list] = mapped_column(JSON, default=list)
    core_tasks: Mapped[list] = mapped_column(JSON, default=list)
    soft_skills: Mapped[list] = mapped_column(JSON, default=list)
    certificates: Mapped[list] = mapped_column(JSON, default=list)
    top_cities: Mapped[list] = mapped_column(JSON, default=list)
    top_industries: Mapped[list] = mapped_column(JSON, default=list)

    # 软能力权重
    soft_skill_weights: Mapped[dict] = mapped_column(JSON, default=dict)

    # AI 冲击参数
    ai_velocity: Mapped[int] = mapped_column(Integer, default=5)
    physical_tag: Mapped[bool] = mapped_column(Boolean, default=False)

    # 协作等级
    collab_level_required: Mapped[int] = mapped_column(Integer, default=3)
    collab_tools: Mapped[list] = mapped_column(JSON, default=list)
    collab_weeks_to_next: Mapped[int] = mapped_column(Integer, default=6)
    human_tasks: Mapped[list] = mapped_column(JSON, default=list)

    # O*NET 映射
    onet_soc_codes: Mapped[list] = mapped_column(JSON, default=list)

    # 职业层级（垂直晋升）
    career_level: Mapped[int] = mapped_column(Integer, default=2)  # 1-5
    career_level_label: Mapped[str] = mapped_column(String(16), default="mid")

    # 子方向标签（用于自动连接里程碑节点）
    sub_track: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # 是否为里程碑节点（高级/架构师/总监）
    is_milestone: Mapped[bool] = mapped_column(Boolean, default=False)

    # JD驱动的例行化评分（0=完全创造性，100=完全机械重复）
    routine_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # 关系
    scores: Mapped[list["JobScore"]] = relationship(
        "JobScore", back_populates="node", cascade="all, delete-orphan"
    )


class JobNodeIntro(Base):
    """LLM 生成的岗位简介缓存"""
    __tablename__ = "job_node_intros"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    intro: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class JobEdge(Base):
    __tablename__ = "job_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("job_nodes.node_id"), nullable=False, index=True
    )
    target_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("job_nodes.node_id"), nullable=False, index=True
    )
    edge_type: Mapped[str] = mapped_column(String(32), default="transition")
    difficulty: Mapped[str] = mapped_column(String(8), default="中")
    transition_hours: Mapped[int] = mapped_column(Integer, default=80)
    gap_skills: Mapped[list] = mapped_column(JSON, default=list)
    reason: Mapped[str] = mapped_column(Text, default="")


class JobScore(Base):
    __tablename__ = "job_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("job_nodes.node_id"),
        unique=True,
        nullable=False,
        index=True,
    )

    # 双轴坐标（新命名）
    replacement_pressure: Mapped[float] = mapped_column(Float, default=50.0)
    human_ai_leverage: Mapped[float] = mapped_column(Float, default=50.0)
    zone: Mapped[str] = mapped_column(String(16), default="transition")
    data_quality: Mapped[str] = mapped_column(String(16), default="low")

    # 评分分项
    pressure_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    leverage_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)

    # 时间轴预测
    runway_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    critical_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_projections: Mapped[dict] = mapped_column(JSON, default=dict)

    # 覆盖率与 TRAI/CAI
    coverage_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    theoretical_pressure: Mapped[float | None] = mapped_column(Float, nullable=True)
    trai_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    cai_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)

    scored_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    # 关系
    node: Mapped["JobNode"] = relationship("JobNode", back_populates="scores")


class OnetJob(Base):
    __tablename__ = "onet_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    occ_code: Mapped[str] = mapped_column(
        String(16), unique=True, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    observed_exposure: Mapped[float] = mapped_column(Float, default=0.0)


class OnetTask(Base):
    __tablename__ = "onet_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_name: Mapped[str] = mapped_column(
        Text, unique=True, nullable=False, index=True
    )
    penetration: Mapped[float] = mapped_column(Float, default=0.0)


class TaskAutomation(Base):
    __tablename__ = "task_automation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_name: Mapped[str] = mapped_column(
        Text, unique=True, nullable=False, index=True
    )
    directive: Mapped[float] = mapped_column(Float, default=0.0)
    feedback_loop: Mapped[float] = mapped_column(Float, default=0.0)
    task_iteration: Mapped[float] = mapped_column(Float, default=0.0)
    validation: Mapped[float] = mapped_column(Float, default=0.0)
    learning: Mapped[float] = mapped_column(Float, default=0.0)
    filtered: Mapped[float] = mapped_column(Float, default=0.0)


class TaskMatching(Base):
    __tablename__ = "task_matching"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("job_nodes.node_id"), nullable=False, index=True
    )
    chinese_task: Mapped[str] = mapped_column(Text, nullable=False)
    onet_task: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)


class ScoreChangelog(Base):
    __tablename__ = "score_changelogs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    node_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("job_nodes.node_id"), nullable=False, index=True
    )
    field: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # replacement_pressure | human_ai_leverage | zone
    old_value: Mapped[str] = mapped_column(String(64), nullable=False)
    new_value: Mapped[str] = mapped_column(String(64), nullable=False)
    delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)


class RescoreRun(Base):
    __tablename__ = "rescore_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    triggered_by: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # scheduler | manual
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_nodes: Mapped[int] = mapped_column(Integer, default=0)
    changed_nodes: Mapped[int] = mapped_column(Integer, default=0)
    zone_changes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        String(16), default="running"
    )  # running | completed | failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
