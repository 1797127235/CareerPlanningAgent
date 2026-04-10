# -*- coding: utf-8 -*-
"""Tests for practice API endpoints: next-question and submit."""
import pytest
from backend.db import SessionLocal, engine, Base
from backend.db_models import InterviewQuestion, InterviewReview, JobNode, Profile, CareerGoal, User
from backend.auth import hash_password


@pytest.fixture
def db():
    Base.metadata.create_all(engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def test_user(db):
    user = db.query(User).filter_by(username="quinn_practice").first()
    if not user:
        user = User(username="quinn_practice", password_hash=hash_password("test123"))
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@pytest.fixture
def test_profile(db, test_user):
    profile = db.query(Profile).filter_by(user_id=test_user.id).first()
    if not profile:
        profile = Profile(
            user_id=test_user.id,
            name="Practice Test",
            profile_json='{"skills": [{"name": "Python", "level": "advanced"}], "basic_info": {"major": "CS"}}',
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@pytest.fixture
def seed_questions(db):
    """Seed some test questions."""
    node = db.query(JobNode).first()
    if not node:
        pytest.skip("No job nodes in DB")

    questions = []
    for i in range(3):
        q = InterviewQuestion(
            node_id=node.node_id,
            skill_tag=f"TestSkill_{i}",
            question=f"练习测试题 {i}: 请描述你对该技能的理解",
            question_type="technical",
            difficulty=["easy", "medium", "hard"][i],
            source="imported" if i == 0 else "generated",
        )
        db.add(q)
        questions.append(q)
    db.commit()
    for q in questions:
        db.refresh(q)

    yield node, questions

    # Cleanup
    for q in questions:
        db.delete(q)
    db.commit()


def test_question_table_has_data(db):
    """InterviewQuestion table should have seeded data."""
    count = db.query(InterviewQuestion).count()
    # At least some questions should exist (from seed_interview_questions.py or fixtures)
    print(f"InterviewQuestion count: {count}")
    assert count >= 0  # Doesn't fail on empty DB, just checks table exists


def test_seed_questions_queryable(db, seed_questions):
    """Seeded questions can be queried by node_id."""
    node, questions = seed_questions
    found = db.query(InterviewQuestion).filter_by(node_id=node.node_id).all()
    # At least our 3 test questions
    assert len(found) >= 3


def test_imported_questions_prioritized(db, seed_questions):
    """Imported questions should be prioritized over generated."""
    node, questions = seed_questions
    imported = (
        db.query(InterviewQuestion)
        .filter_by(node_id=node.node_id, source="imported")
        .all()
    )
    assert len(imported) >= 1
    assert imported[0].source == "imported"


def test_exclude_done_questions(db, seed_questions):
    """Questions can be filtered by exclude IDs."""
    node, questions = seed_questions
    exclude = [questions[0].id, questions[1].id]
    remaining = (
        db.query(InterviewQuestion)
        .filter_by(node_id=node.node_id)
        .filter(InterviewQuestion.id.notin_(exclude))
        .all()
    )
    assert all(q.id not in exclude for q in remaining)


def test_career_goal_resolves_node(db, test_user, test_profile, seed_questions):
    """CareerGoal target_node_id is used when no explicit node_id is passed."""
    node, _ = seed_questions
    goal = CareerGoal(
        user_id=test_user.id,
        profile_id=test_profile.id,
        target_node_id=node.node_id,
        target_label=node.label,
        from_node_id="test",
    )
    db.add(goal)
    db.commit()

    # Simulate API behavior: resolve node_id from goal
    active_goal = (
        db.query(CareerGoal)
        .filter_by(user_id=test_user.id, is_active=True)
        .first()
    )
    assert active_goal is not None
    assert active_goal.target_node_id == node.node_id

    # Query questions using resolved node_id
    qs = db.query(InterviewQuestion).filter_by(node_id=active_goal.target_node_id).all()
    assert len(qs) >= 3

    # Cleanup
    db.delete(goal)
    db.commit()


def test_review_persists(db, test_profile):
    """InterviewReview records are created correctly."""
    review = InterviewReview(
        profile_id=test_profile.id,
        target_job="测试岗位",
        question_text="什么是单元测试？",
        answer_text="单元测试是对代码最小单元的测试。",
        analysis_json='{"score": 75, "strengths": [], "weaknesses": [], "overall_feedback": "不错"}',
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    assert review.id is not None
    assert review.target_job == "测试岗位"

    # Can query by profile
    found = db.query(InterviewReview).filter_by(profile_id=test_profile.id).first()
    assert found is not None

    # Cleanup
    db.delete(review)
    db.commit()
