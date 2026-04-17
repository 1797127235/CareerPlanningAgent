"""成长教练 — 按对话情境加载 skill，pull-based context。

设计：
- BASE_IDENTITY 极简（身份 + 格式 + 工具原则）
- skill 清单（name + description + body）由 supervisor 运行时从 agent/skills/*/SKILL.md 加载后注入
- 画像/目标/市场数据通过 pull tool 按需查询（不再 push 到 system prompt）
"""
from __future__ import annotations

from langchain.agents import create_agent as create_react_agent

from agent.llm import get_chat_model
from agent.tools.coach_context_tools import (
    get_user_profile, get_career_goal, get_market_signal, get_memory_recall,
    get_recommended_roles, save_profile_from_chat,
)
from agent.tools.graph_tools import recommend_jobs, search_jobs
from agent.tools.search_tools import search_real_jd


BASE_IDENTITY = """你是"职途智析"的成长教练。

## 回复格式
- 2-5 句，平实直接
- 禁止 markdown/emoji/客服腔
- 只用 tool 返回的数据或系统消息里明确给的数据
- 不编百分比/薪资/倍数；不知道就说不知道

## 工具使用原则
- 需要用户画像/目标/市场数据时，主动调 get_user_profile / get_career_goal / get_market_signal
- 用户说"还记得/上次聊到"时，调 get_memory_recall
- 用户明确请求"帮我搜 JD / 推荐方向"时，才调 search_real_jd / recommend_jobs
- "好/嗯/可以" 是确认不是执行指令，默认不触发工具

## 可用场景 skill
以下是可用的场景 skill。读用户本轮消息后，**自行判断**应用哪一个（也可以都不应用，此时按默认工具原则回应）：

{AVAILABLE_SKILLS}

## 当前用户状态
{CONTEXT}
"""


def create_coach_agent():
    """Create the growth coach agent with pull-based context + skill system.

    NOTE: system_prompt 留 None，运行时由 supervisor 动态构造 SystemMessage 注入
    （BASE_IDENTITY 里的 {AVAILABLE_SKILLS} 和 {CONTEXT} 占位符由 supervisor 填充）。
    """
    model = get_chat_model(temperature=0.5)
    return create_react_agent(
        model=model,
        tools=[
            get_user_profile,
            get_career_goal,
            get_market_signal,
            get_memory_recall,
            get_recommended_roles,
            save_profile_from_chat,
            search_real_jd,
            recommend_jobs,
            search_jobs,
        ],
        name="coach_agent",
        system_prompt=None,
    )
