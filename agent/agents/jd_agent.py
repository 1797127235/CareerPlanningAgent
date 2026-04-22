"""JD诊断师 — Workflow pattern: 确定性工具调用 + LLM 格式化回复。

设计变更（2026-04-11）：
  从 ReAct agent 改成 2 节点 workflow：
    START → diagnose (code, no LLM) → format (LLM only for NL) → END

为什么用 workflow 而不是 ReAct agent：
  JD 诊断的控制流是固定的（收到消息 → 必须调 JDService → 必须返回结果），
  ReAct 模式让 LLM 决定每一步，会出现"LLM 拒绝调工具""LLM 忘带 marker"等问题。
  LangGraph 官方文档区分 workflow vs agent：
    - fixed control flow → workflow
    - dynamic decisions → agent
  JD 诊断属于前者。

架构保证：
  1. 工具调用一定执行（不再依赖 LLM 判断）
  2. CoachResult 一定创建
  3. [COACH_RESULT_ID:N] 由代码追加（不依赖 LLM 记得）
  4. supervisor 对这个 agent 的调用协议不变（ContextVar 注入 + invoke messages）
"""
from __future__ import annotations

import json
import logging
import re
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from agent.llm import get_chat_model
from agent.tools.jd_tools import (
    _auto_link_diagnosis_to_application,
    _injected_profile,
    _injected_user_id,
    _save_jd_coach_result,
)

logger = logging.getLogger(__name__)


# ── Workflow state ─────────────────────────────────────────────────────────

class JDAgentState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    jd_result: dict | None
    coach_result_id: int | None


# ── Prefix cleaner for JD chip-triggered messages ──────────────────────────

_JD_PREFIX_RE = re.compile(
    r'^(请|帮我|能)?(诊断|分析|看看|评估)[一下]?([这那]份)?([JDjd]+|这个|这份)?(的)?(匹配度|情况|结果|适合度)?\s*[:：]?\s*'
)


def _extract_jd_text(messages: list[BaseMessage]) -> str:
    """从最后一条 HumanMessage 里取 JD 文本，去掉常见指令前缀。"""
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            text = str(m.content or "").strip()
            # Strip common prefixes
            cleaned = _JD_PREFIX_RE.sub('', text).strip()
            # If cleanup removed too much, keep original
            return cleaned if len(cleaned) >= 30 else text
    return ""


def _load_profile_fallback() -> dict:
    """If ContextVar profile not set, load from DB using injected user_id."""
    try:
        user_id = _injected_user_id.get()
        if not user_id:
            return {}
        from backend.db import SessionLocal
        from backend.models import Profile

        db = SessionLocal()
        try:
            p = (
                db.query(Profile)
                .filter_by(user_id=user_id)
                .order_by(Profile.updated_at.desc())
                .first()
            )
            if p:
                return json.loads(p.profile_json or "{}")
        finally:
            db.close()
    except Exception:
        logger.exception("Profile fallback load failed")
    return {}


# ── Node 1: deterministic diagnosis ─────────────────────────────────────────

def _run_diagnosis(state: JDAgentState) -> dict:
    """Run JDService.diagnose() directly. No LLM involved in the decision."""
    jd_text = _extract_jd_text(state.get("messages") or [])

    # Guard 1: no meaningful JD text
    if not jd_text or len(jd_text) < 30:
        return {"jd_result": {"_no_jd": True}, "coach_result_id": None}

    # Guard 2: no profile
    profile = _injected_profile.get() or _load_profile_fallback()
    if not profile:
        return {"jd_result": {"_no_profile": True}, "coach_result_id": None}

    user_id = _injected_user_id.get()

    # Call JDService directly (bypass LLM tool-decision layer)
    try:
        from backend.services.jd_service import JDService
        result = JDService().diagnose(jd_text, profile)
    except Exception as e:
        logger.exception("JDService.diagnose failed")
        return {"jd_result": {"_error": str(e)}, "coach_result_id": None}

    match_score = result.get("match_score", 0)
    matched = result.get("matched_skills", [])
    gaps = result.get("gap_skills", [])
    jd_title = result.get("jd_title", "")
    company = result.get("company", "")

    # Persist JDDiagnosis (historic record) — required for history page
    try:
        from backend.db import SessionLocal
        from backend.models import JDDiagnosis, Profile as _Profile

        db = SessionLocal()
        try:
            profile_id = None
            if user_id:
                p = (
                    db.query(_Profile)
                    .filter_by(user_id=user_id)
                    .order_by(_Profile.updated_at.desc())
                    .first()
                )
                if p:
                    profile_id = p.id
            if profile_id and user_id:
                db.add(JDDiagnosis(
                    user_id=user_id,
                    profile_id=profile_id,
                    jd_text=jd_text[:5000],
                    jd_title=(jd_title or jd_text[:40])[:256],
                    match_score=match_score,
                    result_json=json.dumps(result, ensure_ascii=False),
                ))
                db.commit()
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to persist JDDiagnosis")

    # Persist CoachResult (for card rendering in chat UI)
    coach_result_id = _save_jd_coach_result(
        jd_text, match_score, matched, gaps, jd_title, user_id=user_id,
        company=company,
    )

    # Best-effort link to existing JobApplication tracking record
    if user_id and jd_title:
        try:
            _auto_link_diagnosis_to_application(jd_title, user_id)
        except Exception:
            pass

    logger.info(
        "JD workflow diagnosed: user=%s match=%d gaps=%d cr_id=%s",
        user_id, match_score, len(gaps), coach_result_id,
    )

    return {"jd_result": result, "coach_result_id": coach_result_id}


# ── Node 2: LLM formats structured result into natural language ─────────────

_FORMAT_PROMPT = """把下面这份 JD 匹配分析的结果口头转述给学生，要求：
- 像职业教练口头说话，3-5 句话
- 不要列表、不要表格、不要分节标题、不要 emoji
- 先说匹配度百分比，再说最大的 1-2 个缺口，最后给一个具体下一步建议
- 不要自我介绍、不要开头问候

JD 匹配结果：
- 岗位: {jd_title}
- 综合匹配度: {match_score}%
- 已匹配技能: {matched}
- 核心缺口: {gaps}

按上面的风格直接生成 3-5 句话的口语化回复（不要加任何额外前缀或后缀）："""


def _format_response(state: JDAgentState) -> dict:
    """Use LLM only for natural-language formatting of the result."""
    result = state.get("jd_result") or {}
    coach_result_id = state.get("coach_result_id")

    # Edge cases: return fixed messages, no LLM call
    if result.get("_no_jd"):
        return {"messages": [AIMessage(
            content="你还没发 JD 文本过来。把想诊断的岗位描述贴给我，我来分析匹配度和缺口。",
            name="jd_agent",
        )]}
    if result.get("_no_profile"):
        return {"messages": [AIMessage(
            content="还没找到你的画像，先上传简历建立画像后，我再帮你做 JD 诊断。",
            name="jd_agent",
        )]}
    if result.get("_error"):
        return {"messages": [AIMessage(
            content=f"JD 诊断时遇到技术问题：{result['_error']}，稍后再试。",
            name="jd_agent",
        )]}

    match_score = result.get("match_score", 0)
    matched = result.get("matched_skills", [])
    gaps_raw = result.get("gap_skills", [])
    jd_title = result.get("jd_title") or "这份JD"

    matched_str = "、".join(matched[:5]) if matched else "无明显匹配"
    gap_names: list[str] = []
    for g in gaps_raw[:5]:
        if isinstance(g, dict):
            name = g.get("skill", "")
            if name:
                gap_names.append(name)
        elif g:
            gap_names.append(str(g))
    gaps_str = "、".join(gap_names) if gap_names else "暂无明显缺口"

    prompt = _FORMAT_PROMPT.format(
        match_score=match_score,
        matched=matched_str,
        gaps=gaps_str,
        jd_title=jd_title,
    )

    # LLM call — ONLY for formatting, not for deciding
    try:
        llm = get_chat_model(temperature=0.3)
        response = llm.invoke([HumanMessage(content=prompt)])
        nl_text = str(response.content or "").strip()
        if not nl_text:
            raise ValueError("empty LLM response")
    except Exception:
        logger.exception("LLM format failed, using fallback text")
        # Deterministic fallback — still useful
        nl_text = (
            f"「{jd_title}」匹配度 {match_score}%。"
            f"最大缺口是 {gaps_str}。"
            f"建议先针对性补强这几项技能再投。"
        )

    # Append marker via code — NOT LLM's responsibility
    if coach_result_id:
        nl_text = f"{nl_text} [COACH_RESULT_ID:{coach_result_id}]"

    return {"messages": [AIMessage(content=nl_text, name="jd_agent")]}


# ── Graph builder ──────────────────────────────────────────────────────────

def create_jd_agent():
    """Build the JD diagnosis workflow graph.

    START → diagnose (deterministic) → format (LLM for natural language) → END

    The graph is invoked by supervisor via `agent.invoke({"messages": [...]})`.
    ContextVars (_injected_profile, _injected_user_id) are set by supervisor
    before invoke, read by _run_diagnosis, and reset after.
    """
    graph = StateGraph(JDAgentState)
    graph.add_node("diagnose", _run_diagnosis)
    graph.add_node("format", _format_response)
    graph.add_edge(START, "diagnose")
    graph.add_edge("diagnose", "format")
    graph.add_edge("format", END)
    return graph.compile(name="jd_agent")
