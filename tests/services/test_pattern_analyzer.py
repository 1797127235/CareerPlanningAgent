"""Tests for pattern_analyzer."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

import json

from backend.db_models import User, JDDiagnosis, Profile, ProjectRecord
from backend.services.pattern_analyzer import analyze_user, run_pattern_analysis_all


class TestAnalyzeUser:
    def test_data_insufficient(self, db_session):
        user = User(username="pa_insufficient", password_hash="x")
        db_session.add(user)
        db_session.commit()
        assert analyze_user(db_session, user.id) == ["数据不足"]

    def test_search_type_decision(self, db_session):
        user = User(username="pa_search", password_hash="x")
        db_session.add(user)
        db_session.flush()
        for i in range(6):
            db_session.add(JDDiagnosis(
                user_id=user.id,
                profile_id=1,
                jd_text="...",
                jd_title=f"岗位{i}",
                match_score=50,
                created_at=datetime.now(timezone.utc),
            ))
        db_session.commit()
        result = analyze_user(db_session, user.id)
        assert "搜索型决策" in result

    def test_repeatedly_stuck(self, db_session):
        user = User(username="pa_stuck", password_hash="x")
        db_session.add(user)
        db_session.flush()
        for _ in range(3):
            db_session.add(JDDiagnosis(
                user_id=user.id,
                profile_id=1,
                jd_text="...",
                jd_title="同一岗位",
                match_score=50,
                created_at=datetime.now(timezone.utc),
            ))
        db_session.commit()
        result = analyze_user(db_session, user.id)
        assert "反复纠结" in result


class TestRunPatternAnalysisAll:
    @patch("backend.services.coach_memory.get_memory")
    def test_writes_patterns_to_mem0(self, mock_get_memory, db_session):
        user = User(username="pa_run", password_hash="x")
        db_session.add(user)
        db_session.flush()
        profile = Profile(user_id=user.id, name="Test", profile_json="{}")
        db_session.add(profile)
        db_session.flush()
        for _ in range(3):
            db_session.add(JDDiagnosis(
                user_id=user.id,
                profile_id=profile.id,
                jd_text="...",
                jd_title="同一岗位",
                match_score=50,
                created_at=datetime.now(timezone.utc),
            ))
        db_session.commit()

        mock_mem = MagicMock()
        mock_get_memory.return_value = mock_mem

        count = run_pattern_analysis_all()
        assert count >= 1
        # Mem0 add 被调用，且内容包含 [行为模式分析]
        calls = mock_mem.add.call_args_list
        assert any("[行为模式分析]" in str(c.args[0]) for c in calls)
        # 元数据正确
        assert any(c.kwargs.get("metadata") == {"kind": "pattern_analysis"} for c in calls)
