"""Tests for coach_agent M0苏格拉底范式 prompt."""
from __future__ import annotations

import pytest

from agent.agents.coach_agent import SYSTEM_PROMPT, create_coach_agent


class TestSystemPrompt:
    def test_contains_grow_structure(self):
        assert "GROW 对话结构" in SYSTEM_PROMPT
        assert "G - Goal" in SYSTEM_PROMPT
        assert "R - Reality" in SYSTEM_PROMPT
        assert "O - Options" in SYSTEM_PROMPT
        assert "W - Will" in SYSTEM_PROMPT

    def test_contains_socratic_principle(self):
        assert "苏格拉底式提问" in SYSTEM_PROMPT
        assert "以问题推进对话，不以建议结尾" in SYSTEM_PROMPT

    def test_contains_tool_rules(self):
        assert "工具调用规则" in SYSTEM_PROMPT
        assert '用户说"好"' in SYSTEM_PROMPT
        assert "绝不调工具" in SYSTEM_PROMPT
        assert "search_real_jd" in SYSTEM_PROMPT
        assert "recommend_jobs" in SYSTEM_PROMPT

    def test_contains_stage_adjustments(self):
        assert "lost（方向迷茫）" in SYSTEM_PROMPT
        assert "know_gap（有方向缺技能）" in SYSTEM_PROMPT
        assert "ready（技能够缺机会）" in SYSTEM_PROMPT
        assert "not_started（刚开始考虑）" in SYSTEM_PROMPT

    def test_contains_project_planning_exception(self):
        assert "项目规划场景例外" in SYSTEM_PROMPT
        assert "[项目规划请求]" in SYSTEM_PROMPT

    def test_contains_handoff_context_rule(self):
        assert "[调用背景]" in SYSTEM_PROMPT
        assert "不要调工具" in SYSTEM_PROMPT


class TestCreateCoachAgent:
    def test_signature_unchanged(self):
        agent = create_coach_agent()
        assert agent is not None
        assert agent.name == "coach_agent"
