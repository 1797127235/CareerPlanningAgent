"""Tests for heartbeat_service."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.db_models import UserNotification, User
from backend.services.heartbeat_service import _recently_sent, run_heartbeat


class TestRecentlySent:
    def test_recently_sent_true_within_window(self, db_session):
        user = User(username="hb_test_1", password_hash="x")
        db_session.add(user)
        db_session.flush()
        note = UserNotification(
            user_id=user.id,
            kind="jd_followup",
            title="t",
            body="b",
            created_at=datetime.now(timezone.utc) - timedelta(days=3),
        )
        db_session.add(note)
        db_session.commit()
        assert _recently_sent(db_session, user.id, "jd_followup") is True

    def test_recently_sent_false_outside_window(self, db_session):
        user = User(username="hb_test_2", password_hash="x")
        db_session.add(user)
        db_session.flush()
        note = UserNotification(
            user_id=user.id,
            kind="jd_followup",
            title="t",
            body="b",
            created_at=datetime.now(timezone.utc) - timedelta(days=8),
        )
        db_session.add(note)
        db_session.commit()
        assert _recently_sent(db_session, user.id, "jd_followup") is False

    def test_recently_sent_false_no_record(self, db_session):
        user = User(username="hb_test_3", password_hash="x")
        db_session.add(user)
        db_session.commit()
        assert _recently_sent(db_session, user.id, "inactive_nudge") is False


class TestRunHeartbeat:
    def test_run_heartbeat_returns_stats(self, db_session):
        stats = run_heartbeat()
        assert "jd_followup" in stats
        assert "inactive_nudge" in stats
        assert "milestone_due" in stats
