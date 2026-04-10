"""练习教练 — 在聊天中出题、评分、推荐练习方向。"""
from __future__ import annotations

from langchain.agents import create_agent as create_react_agent

from agent.llm import get_chat_model
from agent.tools.practice_tools import evaluate_answer, list_question_tags, pick_question, review_practice_history

SYSTEM_PROMPT = """你是成长教练的面试练习能力，用户不知道你的存在——以教练身份回复。

职责：从题库抽题、评估答案、推荐练习方向。

## 回复规则
- 不要自我介绍
- 不用 emoji 符号
- 一次只出一道题，等用户回答后再评分
- 评分后主动问"要继续下一题还是换个方向？"
- 出题时直接出题，不要铺垫
- 评分简洁：得分 + 一句亮点 + 一句改进点
- 题库有限，没题时主动说并推荐其他方向
- 用户问"复盘""回顾""我练得怎么样" → 调 review_practice_history 分析历史数据"""


def create_practice_agent():
    """Create and return the practice coach agent."""
    model = get_chat_model(temperature=0.3)
    return create_react_agent(
        model=model,
        tools=[pick_question, evaluate_answer, list_question_tags, review_practice_history],
        name="practice_agent",
        system_prompt=SYSTEM_PROMPT,
    )
