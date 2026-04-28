"""
backend2/db/session.py — v2 独立 DB engine + Session。

使用同一个 SQLite 文件，但拥有自己的 engine 和 session factory。
ORM 模型从 backend.models 导入（共享数据库 schema）。
"""
from __future__ import annotations

from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend2.core.config import DB_PATH


class Base(DeclarativeBase):
    pass


def _build_engine():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{DB_PATH.as_posix()}"
    eng = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(eng, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return eng


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def init_db() -> None:
    """Create all tables if they don't exist (idempotent)."""
    from backend.models import (  # noqa: F401 - shared ORM models
        User, Report, Profile, ProfileParse, CareerGoal,
        JobNode, JobEdge, JobScore,
        GrowthSnapshot, SkillUpdate, ActionProgress,
        ActionPlanV2, PlanWeekProgress,
        ChatSession, ChatMessage,
        JobApplication, InterviewDebrief,
        JDDiagnosis,
        JobNodeIntro, InterviewQuestionBank,
        UserNotification, CoachResult, MockInterview, GrowthEntry,
        ProjectRecord, ProjectLog, InterviewRecord,
        SjtSession,
    )
    Base.metadata.create_all(bind=engine)
    # Migrate: add columns for save-profile pipeline
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE profiles ADD COLUMN active_parse_id INTEGER REFERENCES profile_parses(id)"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_profiles_active_parse_id ON profiles(active_parse_id)"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE profiles ADD COLUMN is_edited BOOLEAN NOT NULL DEFAULT 0"))
            conn.commit()
        except Exception:
            pass


def get_db():
    """FastAPI dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
