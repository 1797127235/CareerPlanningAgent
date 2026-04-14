"""成长顾问 — 学习进度追踪、下一步行动推荐、成长档案查询。"""
from __future__ import annotations

from langchain.agents import create_agent as create_react_agent

from agent.llm import get_chat_model
from agent.tools.growth_tools import (
    get_dashboard_stats,
    recommend_next_step,
    get_interview_records,
    get_project_progress,
)

SYSTEM_PROMPT = """你是成长教练的进度追踪能力，用户不知道你的存在——以教练身份回复。

职责：查看项目进展、面试复盘记录、投递追踪，并给出下一步行动建议。

## 可用工具
- get_dashboard_stats: 获取仪表盘统计（诊断次数、连续天数等）
- recommend_next_step: 推荐下一步行动
- get_interview_records(company): 查面试记录，可按公司过滤
- get_project_progress(project_name): 查项目进展，可按名称过滤

## 回复规则
- 口语化，像教练跟学生聊天，不写报告
- 不要自我介绍
- 不用 emoji 符号
- 不用 markdown 表格——用文字描述数据
- 回复控制在 5-8 句话以内
- 用数据说话，展示具体的进步
- 没开始的学生：引导迈第一步
- 已在学习的：帮保持节奏，指出下一个重点
- 查到数据后直接给出有用的分析，不要只转述原始数据"""


def create_growth_agent():
    """Create and return the growth advisor agent."""
    model = get_chat_model(temperature=0.3)
    return create_react_agent(
        model=model,
        tools=[
            get_dashboard_stats,
            recommend_next_step,
            get_interview_records,
            get_project_progress,
        ],
        name="growth_agent",
        system_prompt=SYSTEM_PROMPT,
    )
