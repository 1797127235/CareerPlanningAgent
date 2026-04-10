"""Test that tools are importable and have correct signatures."""
from __future__ import annotations

import pytest
from langchain_core.tools import BaseTool


class TestToolImports:
    def test_graph_tools_importable(self):
        from agent.tools.graph_tools import get_escape_routes, get_job_detail, search_jobs

        assert isinstance(search_jobs, BaseTool)
        assert isinstance(get_job_detail, BaseTool)
        assert isinstance(get_escape_routes, BaseTool)

    def test_profile_tools_importable(self):
        from agent.tools.profile_tools import get_user_profile, locate_on_graph, score_profile

        assert isinstance(locate_on_graph, BaseTool)
        assert isinstance(get_user_profile, BaseTool)
        assert isinstance(score_profile, BaseTool)

    def test_jd_tools_importable(self):
        from agent.tools.jd_tools import diagnose_jd, get_jd_history

        assert isinstance(diagnose_jd, BaseTool)
        assert isinstance(get_jd_history, BaseTool)

    def test_practice_tools_importable(self):
        from agent.tools.practice_tools import evaluate_answer, list_question_tags, pick_question

        assert isinstance(pick_question, BaseTool)
        assert isinstance(evaluate_answer, BaseTool)
        assert isinstance(list_question_tags, BaseTool)

    def test_growth_tools_importable(self):
        from agent.tools.growth_tools import get_dashboard_stats, recommend_next_step

        assert isinstance(get_dashboard_stats, BaseTool)
        assert isinstance(recommend_next_step, BaseTool)


class TestToolExecution:
    def test_search_jobs_returns_string(self):
        from agent.tools.graph_tools import search_jobs

        result = search_jobs.invoke({"keyword": "前端"})
        assert isinstance(result, str)
        assert "前端" in result or "未找到" in result

    def test_get_job_detail_known(self):
        from agent.tools.graph_tools import get_job_detail

        # Use a label that exists in the graph
        result = get_job_detail.invoke({"job_name": "Java后端工程师"})
        assert isinstance(result, str)

    def test_escape_routes_empty_node(self):
        from agent.tools.graph_tools import get_escape_routes

        result = get_escape_routes.invoke({"node_id": ""})
        assert "定位" in result or "未找到" in result

    def test_diagnose_jd_returns_string(self):
        import json

        from agent.tools.jd_tools import diagnose_jd

        profile = json.dumps({"skills": [{"name": "Python"}, {"name": "SQL"}]})
        result = diagnose_jd.invoke({
            "jd_text": "要求熟悉Python和Java，有MySQL经验",
            "profile_json": profile,
        })
        assert isinstance(result, str)
        assert "匹配度" in result or "出错" in result

    def test_diagnose_jd_empty_jd(self):
        from agent.tools.jd_tools import diagnose_jd

        result = diagnose_jd.invoke({"jd_text": "", "profile_json": "{}"})
        assert "JD" in result or "请提供" in result

    def test_locate_on_graph_returns_string(self):
        import json

        from agent.tools.profile_tools import locate_on_graph

        profile = json.dumps({
            "skills": [{"name": "Python"}, {"name": "Django"}],
            "projects": [{"name": "Web项目", "description": "后端开发"}],
        })
        result = locate_on_graph.invoke({"profile_json": profile})
        assert isinstance(result, str)
        assert "匹配" in result or "定位" in result or "出错" in result

    def test_locate_on_graph_bad_json(self):
        from agent.tools.profile_tools import locate_on_graph

        result = locate_on_graph.invoke({"profile_json": "not-json"})
        assert "格式错误" in result

    def test_recommend_next_step_returns_string(self):
        from agent.tools.growth_tools import recommend_next_step

        # Use a non-existent profile_id; should still return a string
        result = recommend_next_step.invoke({"profile_id": 99999})
        assert isinstance(result, str)


class TestAgentCreation:
    def test_create_profile_agent(self):
        from agent.agents.profile_agent import create_profile_agent

        agent = create_profile_agent()
        assert agent is not None

    def test_create_navigator_agent(self):
        from agent.agents.navigator_agent import create_navigator_agent

        agent = create_navigator_agent()
        assert agent is not None

    def test_create_jd_agent(self):
        from agent.agents.jd_agent import create_jd_agent

        agent = create_jd_agent()
        assert agent is not None

    def test_create_practice_agent(self):
        from agent.agents.practice_agent import create_practice_agent

        agent = create_practice_agent()
        assert agent is not None

    def test_create_growth_agent(self):
        from agent.agents.growth_agent import create_growth_agent

        agent = create_growth_agent()
        assert agent is not None


class TestState:
    def test_career_state_type(self):
        from agent.state import CareerState

        # TypedDict should be usable as a type annotation
        assert CareerState is not None
        # Check that the expected keys are in the annotations
        annotations = CareerState.__annotations__
        assert "messages" in annotations
        assert "current_agent" in annotations
        assert "agent_queue" in annotations
        assert "user_id" in annotations
        assert "profile_id" in annotations
        assert "user_profile" in annotations
        assert "career_goal" in annotations
        assert "current_node_id" in annotations
        assert "user_stage" in annotations
        assert "last_diagnosis" in annotations
        assert "_profile_dirty" in annotations
