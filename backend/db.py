"""
SQLAlchemy database setup — SQLite persistence for users & reports.
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "app_state" / "app.db"


class Base(DeclarativeBase):
    pass


def _build_engine():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{DB_PATH.as_posix()}"
    eng = create_engine(url, connect_args={"check_same_thread": False})

    from sqlalchemy import event

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
    """Create all tables if they don't exist."""
    from backend.db_models import (  # noqa: F401
        User, Report, Profile, CareerGoal,
        Skill, AiToolMapping, JobNode, JobEdge, JobScore,
        OnetJob, OnetTask, TaskAutomation, TaskMatching,
        ScoreChangelog, RescoreRun,
        GrowthSnapshot, SkillUpdate, ActionProgress,
        ActionPlanV2, PlanWeekProgress,
        ChatSession, ChatMessage,
        JobApplication, InterviewDebrief,
        JobNodeIntro, InterviewQuestionBank,
    )
    from backend.market_signal_model import MarketSignal  # noqa: F401
    from backend.city_market_signal_model import CityMarketSignal  # noqa: F401
    Base.metadata.create_all(bind=engine)
    # Migrate: add routine_score column if missing
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE project_records ADD COLUMN graph_data TEXT"))
            conn.commit()
        except Exception:
            pass  # column already exists
        try:
            conn.execute(text("ALTER TABLE project_logs ADD COLUMN task_status VARCHAR(20) DEFAULT 'done'"))
            conn.commit()
        except Exception:
            pass  # column already exists
        try:
            conn.execute(text("ALTER TABLE project_logs ADD COLUMN reflection TEXT"))
            conn.commit()
        except Exception:
            pass  # column already exists
        try:
            conn.execute(text("ALTER TABLE job_nodes ADD COLUMN routine_score FLOAT"))
            conn.commit()
        except Exception:
            pass  # column already exists
        try:
            conn.execute(text("ALTER TABLE interview_reviews ADD COLUMN question_id INTEGER REFERENCES interview_questions(id)"))
            conn.commit()
        except Exception:
            pass  # column already exists
        try:
            conn.execute(text(
                "ALTER TABLE interview_questions ADD COLUMN question_category VARCHAR(32) NOT NULL DEFAULT 'technical'"
            ))
            conn.commit()
        except Exception:
            pass  # column already exists
        try:
            conn.execute(text(
                "CREATE INDEX ix_interview_questions_question_category ON interview_questions(question_category)"
            ))
            conn.commit()
        except Exception:
            pass  # index already exists
        try:
            conn.execute(text("ALTER TABLE career_goals ADD COLUMN is_primary BOOLEAN NOT NULL DEFAULT 0"))
            conn.commit()
        except Exception:
            pass  # column already exists
        try:
            conn.execute(text("CREATE INDEX ix_career_goals_profile_id ON career_goals(profile_id)"))
            conn.commit()
        except Exception:
            pass  # index already exists
        try:
            conn.execute(text("ALTER TABLE profiles ADD COLUMN cached_recs_json TEXT NOT NULL DEFAULT '{}'"))
            conn.commit()
        except Exception:
            pass  # column already exists
        try:
            conn.execute(text("ALTER TABLE profiles ADD COLUMN cached_gaps_json TEXT NOT NULL DEFAULT '{}'"))
            conn.commit()
        except Exception:
            pass  # column already exists
        # 迁移存量数据：每个 profile 的首个 active goal 设为 primary
        try:
            conn.execute(text("""
                UPDATE career_goals
                SET is_primary = 1
                WHERE id IN (
                    SELECT MIN(id) FROM career_goals
                    WHERE is_active = 1
                    GROUP BY profile_id
                )
                AND is_primary = 0
            """))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE profiles ADD COLUMN coach_memo TEXT NOT NULL DEFAULT ''"))
            conn.commit()
        except Exception:
            pass  # column already exists
        # 成长档案: 项目-缺口技能关联
        try:
            conn.execute(text("ALTER TABLE project_records ADD COLUMN gap_skill_links TEXT NOT NULL DEFAULT '[]'"))
            conn.commit()
        except Exception:
            pass  # column already exists
        try:
            conn.execute(text("ALTER TABLE job_applications ADD COLUMN reflection TEXT"))
            conn.commit()
        except Exception:
            pass  # column already exists
        try:
            conn.execute(text("ALTER TABLE interview_records ADD COLUMN stage VARCHAR(32) NOT NULL DEFAULT 'applied'"))
            conn.commit()
        except Exception:
            pass  # column already exists


def get_db():
    """FastAPI dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
