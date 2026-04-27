"""Tests for coach_agent M0苏格拉底范式 prompt."""
from __future__ import annotations

import pytest

from agent.agents.coach_agent import BASE_IDENTITY, create_coach_agent


class TestSystemPrompt:
    def test_contains_grow_structure(self):
        assert "GROW 对话结构" in BASE_IDENTITY or "G - Goal" in BASE_IDENTITY or "目标" in BASE_IDENTITY

    def test_contains_socratic_principle(self):
        assert "苏格拉底式提问" in BASE_IDENTITY
        assert "以问题推进对话，不以建议结尾" in BASE_IDENTITY

    def test_contains_tool_rules(self):
        assert "工具调用规则" in BASE_IDENTITY
        assert '用户说"好"' in BASE_IDENTITY
        assert "绝不调工具" in BASE_IDENTITY
        assert "search_real_jd" in BASE_IDENTITY
        assert "recommend_jobs" in BASE_IDENTITY

    def test_contains_stage_adjustments(self):
        assert "lost（方向迷茫）" in BASE_IDENTITY
        assert "know_gap（有方向缺技能）" in BASE_IDENTITY
        assert "ready（技能够缺机会）" in BASE_IDENTITY
        assert "not_started（刚开始考虑）" in BASE_IDENTITY

    def test_contains_project_planning_exception(self):
        assert "项目规划场景例外" in BASE_IDENTITY
        assert "[项目规划请求]" in BASE_IDENTITY

    def test_contains_handoff_context_rule(self):
        assert "[调用背景]" in BASE_IDENTITY
        assert "不要调工具" in BASE_IDENTITY


class TestCreateCoachAgent:
    def test_signature_unchanged(self):
        agent = create_coach_agent()
        assert agent is not None
        assert agent.name == "coach_agent"
