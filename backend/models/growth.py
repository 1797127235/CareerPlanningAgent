"""Growth log and progress ORM models."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class GrowthSnapshot(Base):
    __tablename__ = "growth_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("profiles.id"), nullable=False, index=True
    )
    report_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    target_node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # initial / stage_complete / deep_reeval
    stage_completed: Mapped[int] = mapped_column(Integer, default=0)
    readiness_score: Mapped[float] = mapped_column(Float, nullable=False)
    base_score: Mapped[float] = mapped_column(Float, nullable=False)
    growth_bonus: Mapped[float] = mapped_column(Float, nullable=False)
    four_dim_detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    action_progress: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class SkillUpdate(Base):
    __tablename__ = "skill_updates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("profiles.id"), nullable=False, index=True
    )
    update_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # skill / project / certificate / internship
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(
        String(20), default="manual"
    )  # manual / action_plan
    applied: Mapped[bool] = mapped_column(Boolean, default=False)
    consumed_by_snapshot_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("growth_snapshots.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class ActionProgress(Base):
    __tablename__ = "action_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("profiles.id"), nullable=False
    )
    report_key: Mapped[str] = mapped_column(String(128), nullable=False)
    checked: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        UniqueConstraint("profile_id", "report_key", name="uq_progress_profile_report"),
    )


class ActionPlanV2(Base):
    __tablename__ = "action_plan_v2"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("profiles.id"), nullable=False, index=True
    )
    report_key: Mapped[str] = mapped_column(String(128), nullable=False)
    stage: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 / 2 / 3
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="generating"
    )
    # generating | ready | stale | failed
    content: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    time_budget: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "profile_id", "report_key", "stage", name="uq_plan_v2_profile_report_stage"
        ),
    )


class PlanWeekProgress(Base):
    __tablename__ = "plan_week_progress"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), index=True)
    report_key: Mapped[str] = mapped_column(String(128), nullable=False)
    stage: Mapped[int] = mapped_column(Integer, nullable=False)
    week_num: Mapped[int] = mapped_column(Integer, nullable=False)
    checked_tasks: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "profile_id", "report_key", "stage", "week_num", name="uq_week_progress"
        ),
    )


class ProjectRecord(Base):
    """用户项目记录 — 做了什么项目、用了什么技能、完成状态"""

    __tablename__ = "project_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    profile_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("profiles.id"), nullable=True, index=True)

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills_used: Mapped[list] = mapped_column(JSON, default=list)     # ["C++", "Redis", "Linux"]
    # 学生主动选择: 这个项目补哪些 gap 技能 (来自 CareerGoal.gap_skills)
    gap_skill_links: Mapped[list] = mapped_column(JSON, default=list)  # ["Redis", "K8s"]
    github_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # planning | in_progress | completed
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="in_progress")
    linked_node_id: Mapped[str | None] = mapped_column(String(128), nullable=True)  # 关联图谱节点
    reflection: Mapped[str | None] = mapped_column(Text, nullable=True)  # 做完了有什么收获

    graph_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # ReactFlow nodes+edges JSON

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class ProjectLog(Base):
    """项目进展/笔记记录"""

    __tablename__ = "project_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project_records.id"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    reflection: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_status: Mapped[str] = mapped_column(String(20), default="done")  # done | in_progress | blocked
    log_type: Mapped[str] = mapped_column(String(20), default="progress")  # progress | note
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class InterviewRecord(Base):
    """简化面试记录 — 轻量版，自由文本 + AI 复盘"""

    __tablename__ = "interview_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    profile_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("profiles.id"), nullable=True, index=True)
    application_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("job_applications.id"), nullable=True)

    company: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    position: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    round: Mapped[str] = mapped_column(String(64), nullable=False, default="技术一面")  # 技术一面/HR面/...
    content_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")   # 自由文本：问了什么
    self_rating: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")  # good|medium|bad
    result: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")  # passed|failed|pending
    stage: Mapped[str] = mapped_column(String(32), nullable=False, default="applied")  # applied|written_test|interviewing|offered|rejected
    reflection: Mapped[str | None] = mapped_column(Text, nullable=True)  # 自己的感受和收获
    ai_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)  # AI生成的复盘分析JSON

    interview_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class GrowthEntry(Base):
    """统一成长档案记录 — 学习笔记 / 面试复盘 / 项目记录 / 计划"""
    __tablename__ = "growth_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)  # project|interview|learning|null
    tags: Mapped[list] = mapped_column(JSON, default=list)

    # 面试/项目的结构化数据；学习笔记为 None
    structured_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # 计划
    is_plan: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(16), default="done")  # done|pending|dropped
    due_type: Mapped[str | None] = mapped_column(String(16), nullable=True)  # daily|weekly|monthly|custom
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # AI 建议
    ai_suggestions: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # 关联（可选）
    linked_project_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("project_records.id"), nullable=True)
    linked_application_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("job_applications.id"), nullable=True)

    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
