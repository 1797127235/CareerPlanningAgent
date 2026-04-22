"""
SQLAlchemy ORM models — User / Report / Profile / Skill / JobNode / JobEdge / JobScore.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    UniqueConstraint,
)
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

    reports: Mapped[list[Report]] = relationship(
        "Report", back_populates="owner", cascade="all, delete-orphan"
    )
    profiles: Mapped[list[Profile]] = relationship(
        "Profile", back_populates="owner", cascade="all, delete-orphan"
    )


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_key: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(256), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    data_json: Mapped[str] = mapped_column(Text, default="{}")  # full report payload
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    owner: Mapped[User] = relationship("User", back_populates="reports")


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

    owner: Mapped[User] = relationship("User", back_populates="profiles")


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


# ── 技能分类表 ──────────────────────────────────────────────────


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


# ── AI 工具映射表 ──────────────────────────────────────────────


class AiToolMapping(Base):
    __tablename__ = "ai_tool_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_name: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    tools: Mapped[list] = mapped_column(JSON, default=list)


# ── 岗位节点表（静态基础数据）────────────────────────────────────


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
    scores: Mapped[list[JobScore]] = relationship(
        "JobScore", back_populates="node", cascade="all, delete-orphan"
    )


class JobNodeIntro(Base):
    """LLM 生成的岗位简介缓存"""
    __tablename__ = "job_node_intros"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    intro: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


# ── 岗位边表（职业转移路径）────────────────────────────────────


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


# ── 岗位评分表（计算结果，可重算）────────────────────────────────


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
    node: Mapped[JobNode] = relationship("JobNode", back_populates="scores")


# ── O*NET 岗位观测暴露度 ──────────────────────────────────────


class OnetJob(Base):
    __tablename__ = "onet_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    occ_code: Mapped[str] = mapped_column(
        String(16), unique=True, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    observed_exposure: Mapped[float] = mapped_column(Float, default=0.0)


# ── O*NET 任务级 AI 渗透率 ────────────────────────────────────


class OnetTask(Base):
    __tablename__ = "onet_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_name: Mapped[str] = mapped_column(
        Text, unique=True, nullable=False, index=True
    )
    penetration: Mapped[float] = mapped_column(Float, default=0.0)


# ── 任务级自动化/增强分解 ─────────────────────────────────────


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


# ── 中文任务 → O*NET 任务语义匹配 ─────────────────────────────


class TaskMatching(Base):
    __tablename__ = "task_matching"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("job_nodes.node_id"), nullable=False, index=True
    )
    chinese_task: Mapped[str] = mapped_column(Text, nullable=False)
    onet_task: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)


# ── 评分变更日志 ─────────────────────────────────────────────


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


# ── 重算运行记录 ─────────────────────────────────────────────


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


# ── 成长循环：快照 / 技能更新 / 行动进度 ──────────────────────────


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

    id: Mapped[int] = mapped_column(primary_key=True)
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


# ── 聊天会话 ──────────────────────────────────────────────────


class ChatSession(Base):
    """聊天会话"""

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    profile_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("profiles.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )


class ChatMessage(Base):
    """聊天消息"""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # 'user' | 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


from backend.services.market_signals import MarketSignal  # noqa: F401
from backend.services.market_signals import CityMarketSignal  # noqa: F401


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


# ── JD 匹配诊断记录 ─────────────────────────────────────────────


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


# ── 求职投递跟踪 ────────────────────────────────────────────────


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


# ── 教练结果存储 ─────────────────────────────────────────────────


# ── 成长档案：项目记录 ──────────────────────────────────────────────


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


# ── 成长档案：项目进展日志 ──────────────────────────────────────────


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


# ── 成长档案：简化面试记录 ──────────────────────────────────────────


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


# ── 教练结果存储 ─────────────────────────────────────────────────


class CoachResult(Base):
    """Structured results from coach agent interactions (JD diagnosis, reports, etc.)."""

    __tablename__ = "coach_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    session_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("chat_sessions.id"), nullable=True
    )
    result_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # jd_diagnosis | career_report | action_plan | interview_review
    title: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    detail_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


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
