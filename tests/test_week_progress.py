import pytest
from backend.models import PlanWeekProgress, ActionPlanV2
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from backend.db import Base

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_create_week_progress(db):
    wp = PlanWeekProgress(
        profile_id=1, report_key="abc", stage=1, week_num=1,
        checked_tasks={"task_abc123": True, "task_def456": False}
    )
    db.add(wp)
    db.commit()
    result = db.query(PlanWeekProgress).first()
    assert result.checked_tasks["task_abc123"] is True
    assert result.week_num == 1

def test_unique_constraint(db):
    wp1 = PlanWeekProgress(profile_id=1, report_key="abc", stage=1, week_num=1, checked_tasks={})
    wp2 = PlanWeekProgress(profile_id=1, report_key="abc", stage=1, week_num=1, checked_tasks={})
    db.add(wp1)
    db.commit()
    db.add(wp2)
    with pytest.raises(Exception):
        db.commit()

def test_time_budget_has_start_date(db):
    plan = ActionPlanV2(
        profile_id=1, report_key="abc", stage=1,
        status="ready",
        time_budget={"hours_per_week": 10, "total_weeks": 12, "start_date": "2026-03-27T00:00:00Z"},
        content={}
    )
    db.add(plan)
    db.commit()
    result = db.query(ActionPlanV2).first()
    assert result.time_budget["start_date"] == "2026-03-27T00:00:00Z"
