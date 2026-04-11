"""岗位搜索员 — Workflow pattern: 确定性工具调用 + LLM 简短介绍。

设计（2026-04-11）：
  跟 jd_agent 用同样的模式，把"找招聘"这条路径从 ReAct agent 抽出来变成 workflow。

  START → run_search (code, 直接调 search_real_jd) → format_intro (LLM 说一句引导) → END

为什么不让 navigator 来做：
  1. navigator 的 system_prompt 是"学长式方向顾问"，8-15 句话讲方向/市场/AI/行动
  2. 遇到"帮我找招聘"时 LLM 会选择继续讲方向，不调 search_real_jd
  3. 而 workflow 模式下，run_search 节点**一定**执行，没有 LLM 拒绝的余地

架构保证：
  1. search_real_jd 一定被调用
  2. 返回的 jd_cards marker 一定出现在 ToolMessage 里（chat.py 能 pick up）
  3. 格式化回复由 LLM 做，但只是一句引导
"""
from __future__ import annotations

import logging
import re
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from agent.llm import get_chat_model
from agent.tools.search_tools import (
    _injected_goal_for_search,
    _injected_profile_for_search,
    search_real_jd,
)

logger = logging.getLogger(__name__)


class SearchAgentState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    search_result: str | None  # raw tool output (includes [JD_SEARCH_RESULTS:..] marker)
    hit_count: int


# ── Extract query from user message ─────────────────────────────────────────

_QUERY_CLEAN_RE = re.compile(
    r'^(请|帮我|能|麻烦你?|可以)?(帮我)?(搜[搜索一下几份]*|找[找几份]*)\s*'
)


def _extract_query(messages: list[BaseMessage]) -> str:
    """Turn the last HumanMessage into a search query."""
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            text = str(m.content or "").strip()
            # Strip leading verbs; what's left is the object phrase
            cleaned = _QUERY_CLEAN_RE.sub('', text).strip()
            return cleaned or text
    return ""


# ── Node 1: deterministic search ────────────────────────────────────────────

def _run_search(state: SearchAgentState) -> dict:
    """Directly invoke search_real_jd. LLM has NO say in whether to call."""
    query = _extract_query(state.get("messages") or [])
    if not query:
        query = "适合学生的岗位 校招"

    # search_real_jd is a @tool — invoke its underlying function via .invoke()
    try:
        tool_output = search_real_jd.invoke({"query": query})
    except Exception as e:
        logger.exception("search_real_jd failed")
        tool_output = f"搜索时出错：{e}"

    # Count JD cards (rough)
    hit_count = tool_output.count('"title"') if "[JD_SEARCH_RESULTS:" in tool_output else 0

    # Also emit a ToolMessage so chat.py's tool_messages list picks up the marker
    # (this is how the frontend gets the JD_SEARCH_RESULTS marker to render cards)
    tool_msg = ToolMessage(
        content=tool_output,
        tool_call_id="search_real_jd_direct",
        name="search_real_jd",
    )

    return {
        "messages": [tool_msg],
        "search_result": tool_output,
        "hit_count": hit_count,
    }


# ── Node 2: brief intro message ─────────────────────────────────────────────

_INTRO_PROMPT = """用户刚通过"找招聘"功能拿到了一批真实的校招 JD 卡片。你要用2-3句话做一个简短引导：
- 告诉用户搜到了多少份
- 建议用户点击感兴趣的卡片做"诊断匹配度"
- 不要列表、不要分节、不要 emoji
- 禁止自己描述 JD 内容，卡片已经在用户界面展示了

上下文：共搜到 {hit_count} 份招聘卡片。

请生成 2-3 句话的引导语："""


def _format_intro(state: SearchAgentState) -> dict:
    """LLM generates a brief one-liner to introduce the results."""
    search_result = state.get("search_result") or ""
    hit_count = state.get("hit_count", 0)

    # If search failed, return the error directly
    if "[JD_SEARCH_RESULTS:" not in search_result:
        return {"messages": [AIMessage(
            content=search_result or "搜索没有返回结果，可以换个关键词再试。",
            name="search_agent",
        )]}

    if hit_count == 0:
        return {"messages": [AIMessage(
            content="没搜到匹配的校招岗位，可以试试更具体的方向（如\"C++ 后端\"或\"字节跳动 算法\"）。",
            name="search_agent",
        )]}

    # Generate brief intro via LLM (optional polish)
    try:
        llm = get_chat_model(temperature=0.4)
        response = llm.invoke([HumanMessage(
            content=_INTRO_PROMPT.format(hit_count=hit_count)
        )])
        intro = str(response.content or "").strip()
        if not intro:
            raise ValueError("empty LLM response")
    except Exception:
        logger.exception("Intro LLM call failed, using fallback")
        intro = f"给你搜到 {hit_count} 份相关招聘，下面是卡片列表，感兴趣的点「诊断匹配度」看你和岗位的差距。"

    return {"messages": [AIMessage(content=intro, name="search_agent")]}


# ── Graph builder ───────────────────────────────────────────────────────────

def create_search_agent():
    """Build the JD search workflow graph.

    START → run_search (deterministic tool call) → format_intro (brief LLM) → END
    """
    graph = StateGraph(SearchAgentState)
    graph.add_node("search", _run_search)
    graph.add_node("intro", _format_intro)
    graph.add_edge(START, "search")
    graph.add_edge("search", "intro")
    graph.add_edge("intro", END)
    return graph.compile(name="search_agent")
