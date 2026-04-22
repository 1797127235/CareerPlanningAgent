"""
tests/conftest.py — shared pytest fixtures.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Graph data ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def graph_data() -> dict:
    """Load the career graph from data/graph.json."""
    graph_path = PROJECT_ROOT / "data" / "graph.json"
    if not graph_path.exists():
        pytest.skip(f"graph.json not found at {graph_path}")
    with graph_path.open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def graph_service():
    """Session-scoped GraphService instance with graph loaded."""
    from backend.services.graph import GraphService
    svc = GraphService()
    svc.load()
    return svc


@pytest.fixture(scope="session")
def profile_service(graph_service):
    """Session-scoped ProfileService instance."""
    from backend.services.profile_service import ProfileService
    return ProfileService(graph_service)


# ── DB engine & session ──────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def db_engine():
    """Create a SQLAlchemy engine pointing at the app SQLite database."""
    db_path = PROJECT_ROOT / "data" / "app_state" / "app.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    # Ensure all tables exist
    from backend.db import Base
    from backend import models  # noqa: F401 — registers all ORM models
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """Yield a transactional Session that rolls back after each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    Session_ = sessionmaker(bind=connection, class_=Session, expire_on_commit=False)
    session = Session_()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


# ── Sample profile ────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def sample_profile() -> dict:
    """A realistic test profile dict for use across tests."""
    return {
        "basic_info": {
            "name": "张三",
            "major": "计算机科学",
            "education": "本科",
            "graduation_year": 2024,
            "gpa": 3.5,
        },
        "skills": [
            {"name": "Python", "level": "熟练"},
            {"name": "SQL", "level": "掌握"},
            {"name": "机器学习", "level": "了解"},
            {"name": "Git", "level": "熟练"},
            {"name": "Linux", "level": "掌握"},
        ],
        "experience": [
            {
                "company": "某科技公司",
                "title": "后端开发实习生",
                "duration_months": 3,
                "description": "负责用户服务接口开发，使用 Django + PostgreSQL",
            }
        ],
        "projects": [
            {
                "name": "校园二手书交易平台",
                "tech_stack": ["Python", "Flask", "MySQL", "Redis"],
                "description": "全栈项目，实现商品展示、搜索、交易流程",
                "role": "主要开发者",
            }
        ],
        "soft_skills": {
            "communication": 3,
            "teamwork": 4,
            "problem_solving": 4,
            "learning_agility": 5,
        },
        "target_job": "后端开发工程师",
    }


# ── Skill taxonomy ────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def skill_taxonomy() -> list[dict]:
    """Load skill_taxonomy.csv from data/."""
    taxonomy_path = PROJECT_ROOT / "data" / "skill_taxonomy.csv"
    if not taxonomy_path.exists():
        pytest.skip(f"skill_taxonomy.csv not found at {taxonomy_path}")
    rows: list[dict] = []
    with taxonomy_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows
