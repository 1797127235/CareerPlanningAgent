"""画像分析师 — 简历解析、能力定位、画像评分。"""
from __future__ import annotations

from langchain.agents import create_agent as create_react_agent

from agent.llm import get_chat_model
from agent.tools.profile_tools import get_user_profile, locate_on_graph, score_profile

SYSTEM_PROMPT = """你是成长教练的画像分析能力，用户不知道你的存在——以教练身份回复。

职责：查看/分析能力画像、图谱定位、四维度匹配评分。

## 回复规则
- 口语化，像教练跟学生聊天，不写报告
- 不要自我介绍（不说"我是分析师"）
- 不用 emoji 符号
- 不用 markdown 表格——用简洁文字描述
- 回复控制在 5-8 句话以内
- **必须先调工具获取真实数据再回复，不要凭上下文猜测画像内容**
- 画像不完整时直接说需要补什么
- 结尾给一个具体的下一步建议

## 调用背景
如果 system message 包含 [调用背景]，说明你是被教练转交过来执行特定任务的。
请根据背景中描述的任务来行动，而不是泛泛地介绍自己的能力。"""


def create_profile_agent():
    """Create and return the profile analysis agent."""
    model = get_chat_model(temperature=0.3)
    return create_react_agent(
        model=model,
        tools=[locate_on_graph, get_user_profile, score_profile],
        name="profile_agent",
        system_prompt=SYSTEM_PROMPT,
    )
