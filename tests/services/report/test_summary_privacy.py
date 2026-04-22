"""Privacy boundary test for report summary builder."""
from __future__ import annotations

import json

import pytest

from backend.services.report import summarize
from backend.models import Profile, User


@pytest.fixture
def user_with_coach_memo(db_session):
    """Create a user whose profile contains sensitive coach_memo."""
    user = User(username="privacy_test_user", password_hash="pbkdf2:sha256:260000$salt$hash")
    db_session.add(user)
    db_session.flush()

    profile = Profile(
        user_id=user.id,
        profile_json=json.dumps({"skills": [{"name": "Python", "level": "intermediate"}]}),
        coach_memo="敏感内容：我在偷偷面试字节",
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return user, profile


def test_summary_never_contains_coach_memo(db_session, user_with_coach_memo):
    user, profile = user_with_coach_memo
    summary = summarize.build_report_summary(
        user.id,
        profile,
        db_session,
        prev_report=None,
        skill_gap_current=None,
    )
    blob = json.dumps(summary, ensure_ascii=False)
    assert "敏感内容" not in blob
    assert "偷偷面试字节" not in blob
    assert "coach_memo" not in blob.lower()
