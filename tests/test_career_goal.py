# -*- coding: utf-8 -*-
"""Tests for CareerGoal model and API endpoints."""
import pytest
from backend.db import SessionLocal, engine, Base
from backend.models import CareerGoal, User, Profile
from backend.auth import hash_password


@pytest.fixture
def db():
    Base.metadata.create_all(engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def test_user(db):
    """Create or get a test user."""
    user = db.query(User).filter_by(username="quinn_test").first()
    if not user:
        user = User(username="quinn_test", password_hash=hash_password("test123"))
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@pytest.fixture
def test_profile(db, test_user):
    """Create or get a test profile."""
    profile = db.query(Profile).filter_by(user_id=test_user.id).first()
    if not profile:
        profile = Profile(
            user_id=test_user.id,
            name="Quinn Test Profile",
            profile_json='{"skills": [{"name": "Python", "level": "advanced"}]}',
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def test_career_goal_model_create(db, test_user, test_profile):
    """CareerGoal can be created with all fields."""
    goal = CareerGoal(
        user_id=test_user.id,
        profile_id=test_profile.id,
        target_node_id="backend_dev",
        target_label="后端开发工程师",
        target_zone="safe",
        gap_skills=[{"name": "Java", "estimated_hours": 40}],
        total_hours=40,
        safety_gain=12.5,
        salary_p50=15000,
        tag="最稳",
        transition_probability=0.78,
        from_node_id="data_analyst",
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)

    assert goal.id is not None
    assert goal.target_label == "后端开发工程师"
    assert goal.is_active is True
    assert goal.gap_skills[0]["name"] == "Java"
    assert goal.transition_probability == 0.78

    # Cleanup
    db.delete(goal)
    db.commit()


def test_career_goal_deactivate_old(db, test_user, test_profile):
    """Setting a new goal deactivates the old one."""
    goal1 = CareerGoal(
        user_id=test_user.id,
        profile_id=test_profile.id,
        target_node_id="frontend_dev",
        target_label="前端开发",
        from_node_id="test",
    )
    db.add(goal1)
    db.commit()
    db.refresh(goal1)
    assert goal1.is_active is True

    # Deactivate old, create new (simulating API behavior)
    db.query(CareerGoal).filter_by(user_id=test_user.id, is_active=True).update({"is_active": False})
    goal2 = CareerGoal(
        user_id=test_user.id,
        profile_id=test_profile.id,
        target_node_id="backend_dev",
        target_label="后端开发",
        from_node_id="test",
    )
    db.add(goal2)
    db.commit()
    db.refresh(goal1)
    db.refresh(goal2)

    assert goal1.is_active is False
    assert goal2.is_active is True

    # Only one active goal
    active = db.query(CareerGoal).filter_by(user_id=test_user.id, is_active=True).all()
    assert len(active) == 1
    assert active[0].target_label == "后端开发"

    # Cleanup
    db.delete(goal1)
    db.delete(goal2)
    db.commit()


def test_career_goal_query_active(db, test_user, test_profile):
    """Can query only active goals."""
    g = CareerGoal(
        user_id=test_user.id,
        profile_id=test_profile.id,
        target_node_id="test_node",
        target_label="测试岗位",
        from_node_id="origin",
        is_active=True,
    )
    db.add(g)
    db.commit()

    active = (
        db.query(CareerGoal)
        .filter_by(user_id=test_user.id, is_active=True)
        .order_by(CareerGoal.set_at.desc())
        .first()
    )
    assert active is not None
    assert active.target_label == "测试岗位"

    # No active after deactivation
    g.is_active = False
    db.commit()
    active2 = db.query(CareerGoal).filter_by(user_id=test_user.id, is_active=True).first()
    assert active2 is None

    # Cleanup
    db.delete(g)
    db.commit()
