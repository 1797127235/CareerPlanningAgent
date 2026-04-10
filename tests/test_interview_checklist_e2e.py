# -*- coding: utf-8 -*-
"""E2E smoke test: seed questions -> build checklist -> update status -> verify stats."""
import pytest
from backend.db import SessionLocal, engine, Base
from backend.db_models import (
    InterviewQuestion, InterviewChecklist, JobNode, Profile,
)


@pytest.fixture
def db():
    Base.metadata.create_all(engine)
    session = SessionLocal()
    yield session
    session.close()


def test_build_and_update_checklist(db):
    """Seed a question, build checklist, update item, check stats."""
    from backend.interview_checklist import build_checklist, update_item_status, checklist_stats

    # Ensure a test node exists
    node = db.query(JobNode).first()
    if not node:
        pytest.skip("No job nodes in DB")

    # Seed a test question
    q = InterviewQuestion(
        node_id=node.node_id,
        skill_tag="TestSkill",
        question="这是一道测试面试题",
        question_type="technical",
        difficulty="easy",
        source="imported",
    )
    db.add(q)
    db.commit()

    # Find a profile
    profile = db.query(Profile).first()
    if not profile:
        pytest.skip("No profiles in DB")

    # Build checklist
    cl = build_checklist(
        profile_id=profile.id,
        target_node_id=node.node_id,
        jd_title="Test JD",
        missing_skills=[{"skill": "TestSkill"}, {"skill": "AnotherSkill"}],
        diagnosis_id=None,
        db=db,
    )
    assert cl.id is not None
    assert len(cl.items) >= 1

    stats = checklist_stats(cl)
    assert stats["total"] >= 1
    assert stats["progress"] == 0  # all not_assessed

    # Update first item to can_answer
    cl2 = update_item_status(cl.id, 0, "can_answer", db)
    assert cl2 is not None
    stats2 = checklist_stats(cl2)
    assert stats2["can_answer"] >= 1
    assert stats2["progress"] > 0

    # Cleanup
    db.delete(cl2)
    db.delete(q)
    db.commit()
