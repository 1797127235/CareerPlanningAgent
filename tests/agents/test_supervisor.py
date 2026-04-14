"""Tests for the Supervisor module (triage + handoff architecture)."""
from __future__ import annotations

import pytest


class TestBuildSupervisor:
    def test_supervisor_compiles(self):
        from agent.supervisor import build_supervisor

        graph = build_supervisor()
        assert graph is not None

    def test_supervisor_has_all_agent_nodes(self):
        from agent.supervisor import build_supervisor

        graph = build_supervisor()
        node_names = list(graph.get_graph().nodes.keys())
        for agent_name in [
            "profile_agent",
            "navigator",
            "jd_agent",
            "growth_agent",
            "coach_agent",
            "search_agent",
        ]:
            assert agent_name in node_names or any(
                agent_name in n for n in node_names
            ), f"Agent '{agent_name}' not found in graph nodes: {node_names}"

    def test_supervisor_has_triage_node(self):
        from agent.supervisor import build_supervisor

        graph = build_supervisor()
        node_names = list(graph.get_graph().nodes.keys())
        assert "triage" in node_names, (
            f"triage not found in graph nodes: {node_names}"
        )

    def test_supervisor_has_handoff_executor(self):
        from agent.supervisor import build_supervisor

        graph = build_supervisor()
        node_names = list(graph.get_graph().nodes.keys())
        assert "handoff_executor" in node_names, (
            f"handoff_executor not found in graph nodes: {node_names}"
        )


class TestHandoffTools:
    def test_handoff_tools_count(self):
        from agent.supervisor import HANDOFF_TOOLS

        # 6 agents = 6 handoff tools
        assert len(HANDOFF_TOOLS) == 6

    def test_handoff_tool_names(self):
        from agent.supervisor import HANDOFF_TOOLS

        names = {t.name for t in HANDOFF_TOOLS}
        expected = {
            "transfer_to_profile_agent",
            "transfer_to_navigator",
            "transfer_to_jd_agent",
            "transfer_to_growth_agent",
            "transfer_to_coach_agent",
            "transfer_to_search_agent",
        }
        assert names == expected, f"Handoff tools mismatch: {names} vs {expected}"


class TestContextSummary:
    def test_empty_state(self):
        from agent.supervisor import build_context_summary

        state = {
            "messages": [],
            "current_agent": "",
            "agent_queue": [],
            "user_id": None,
            "profile_id": None,
            "user_profile": None,
            "career_goal": None,
            "current_node_id": None,
            "user_stage": "unknown",
            "last_diagnosis": None,
            "_profile_dirty": False,
        }
        result = build_context_summary(state)
        assert "未建立" in result
        assert "未设定" in result
        assert "unknown" in result

    def test_populated_state(self):
        from agent.supervisor import build_context_summary

        state = {
            "messages": [],
            "current_agent": "",
            "agent_queue": [],
            "user_id": 1,
            "profile_id": 1,
            "user_profile": {"skills": ["Python"]},
            "career_goal": {"label": "云原生工程师"},
            "current_node_id": "cloud_engineer",
            "user_stage": "beginner",
            "last_diagnosis": {"match_score": 58},
            "_profile_dirty": False,
        }
        result = build_context_summary(state)
        assert "已建立" in result
        assert "云原生工程师" in result
        assert "beginner" in result
        assert "cloud_engineer" in result
        assert "58" in result

    def test_partial_state_no_diagnosis(self):
        from agent.supervisor import build_context_summary

        state = {
            "messages": [],
            "current_agent": "",
            "agent_queue": [],
            "user_id": 1,
            "profile_id": 1,
            "user_profile": {"skills": ["Java"]},
            "career_goal": None,
            "current_node_id": None,
            "user_stage": "no_goal",
            "last_diagnosis": None,
            "_profile_dirty": False,
        }
        result = build_context_summary(state)
        assert "已建立" in result
        assert "未设定" in result
        assert "诊断" not in result

    def test_goal_without_label(self):
        from agent.supervisor import build_context_summary

        state = {
            "messages": [],
            "current_agent": "",
            "agent_queue": [],
            "user_id": 1,
            "profile_id": 1,
            "user_profile": None,
            "career_goal": {"node_id": "abc"},
            "current_node_id": None,
            "user_stage": "unknown",
            "last_diagnosis": None,
            "_profile_dirty": False,
        }
        result = build_context_summary(state)
        assert "未知" in result


class TestQuestionRe:
    def test_matches_question_patterns(self):
        from agent.supervisor import _QUESTION_RE
        assert _QUESTION_RE.search("要不要我帮你搜？")
        assert _QUESTION_RE.search("需要吗")
        assert _QUESTION_RE.search("是否适合？")
        assert _QUESTION_RE.search("怎么样？")
        assert _QUESTION_RE.search("好吗？")
        assert _QUESTION_RE.search("帮你看看")
        assert _QUESTION_RE.search("给你建议")

    def test_does_not_match_statement(self):
        from agent.supervisor import _QUESTION_RE
        assert _QUESTION_RE.search("我觉得你可以关注字节。") is None
        assert _QUESTION_RE.search("这是一个开放建议") is None
        assert _QUESTION_RE.search("先补缺口再投") is None
