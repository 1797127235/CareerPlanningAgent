# -*- coding: utf-8 -*-
"""Tests for interview checklist builder."""
import pytest
from unittest.mock import MagicMock, patch


def test_template_question():
    from backend.interview_checklist import _template_question
    q = _template_question("Redis", "后端开发工程师")
    assert "Redis" in q["question"]
    assert q["status"] == "not_assessed"
    assert q["type"] == "technical"


def test_checklist_stats():
    from backend.interview_checklist import checklist_stats
    mock_cl = MagicMock()
    mock_cl.items = [
        {"status": "can_answer"},
        {"status": "cannot"},
        {"status": "learned"},
        {"status": "not_assessed"},
        {"status": "unsure"},
    ]
    stats = checklist_stats(mock_cl)
    assert stats["total"] == 5
    assert stats["passed"] == 2  # can_answer + learned
    assert stats["progress"] == 40
    assert stats["cannot"] == 1
