"""
Supervisor — triage agent with handoff tools.

Architecture (Swarm-style):
  START → triage → tools_condition
                    ├─ no tool calls → END (direct response, e.g. greetings)
                    └─ tool calls → handoff_executor → agent_X → END

The triage LLM decides in ONE call whether to answer directly or hand off.
No separate routing LLM call. Simple messages get 1 LLM call total.
"""
from __future__ import annotations

import logging
from typing import Annotated

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command

from agent.llm import get_chat_model
from agent.state import CareerState

logger = logging.getLogger(__name__)


# ── Context summary builder ───────────────────────────────────────────────────

def build_context_summary(state: CareerState, for_triage: bool = False) -> str:
    """Create a structured summary from shared state.

    Args:
        state: The shared CareerState.
        for_triage: If True, omit detailed skill/profile data to prevent
                    triage from fabricating data-dependent answers.
    """
    parts = ["当前用户状态："]

    if state.get("user_profile"):
        profile = state["user_profile"]
        skills = profile.get("skills", [])
        if for_triage:
            # Triage only gets status, not details — forces handoff for data questions
            parts.append(f"- 画像: 已建立（{len(skills)} 项技能）")
        else:
            parts.append("- 画像: 已建立")
            if skills:
                names = [s.get("name", "") if isinstance(s, dict) else str(s) for s in skills[:8]]
                parts.append(f"- 用户技能: {', '.join(n for n in names if n)}")
                parts.append(f"- 技能数量: {len(skills)} 项")
        edu = profile.get("education", {})
        if edu and edu.get("degree") and not for_triage:
            parts.append(f"- 学历: {edu.get('degree', '')} · {edu.get('major', '')}")
        # Career preferences
        prefs = profile.get("preferences", {})
        if prefs and not for_triage:
            pref_labels = {
                "work_style": {"tech": "深挖技术", "product": "做产品", "data": "分析数据", "management": "带团队"},
                "value_priority": {"growth": "技术成长", "stability": "薪资稳定", "balance": "工作生活平衡", "innovation": "行业前景"},
                "ai_attitude": {"do_ai": "拥抱AI工具", "avoid_ai": "找AI替代不了的", "no_preference": "看机会"},
                "company_type": {"big_tech": "大厂", "growing": "成长型公司", "startup": "初创", "state_owned": "国企"},
            }
            pref_parts = []
            for key, label_map in pref_labels.items():
                val = prefs.get(key, "")
                if val and val in label_map:
                    pref_parts.append(label_map[val])
            if pref_parts:
                parts.append(f"- 就业意愿: {' / '.join(pref_parts)}")
                import json as _json
                parts.append(f"- 意愿数据(JSON): {_json.dumps(prefs, ensure_ascii=False)}")
    else:
        parts.append("- 画像: 未建立（建议先上传简历）")

    if state.get("career_goal"):
        goal = state["career_goal"]
        parts.append(f"- 目标岗位: {goal.get('label', '未知')}")
        if goal.get("zone"):
            zone_names = {"safe": "安全区", "thrive": "成长区", "transition": "转型区", "danger": "风险区"}
            parts.append(f"- 目标区域: {zone_names.get(goal['zone'], goal['zone'])}")
    else:
        parts.append("- 目标岗位: 未设定（建议去画像页查看推荐方向）")

    stage = state.get("user_stage", "unknown")
    stage_labels = {
        "no_profile": "未建画像",
        "has_profile": "已有画像，未做JD诊断",
        "first_diagnosis": "已做首次JD诊断",
        "training": "面试训练中",
        "growing": "持续成长中",
        "report_ready": "可生成报告",
    }
    parts.append(f"- 当前阶段: {stage_labels.get(stage, stage)}")

    if state.get("current_node_id"):
        parts.append(f"- 图谱定位: {state['current_node_id']}")

    if state.get("last_diagnosis"):
        diag = state["last_diagnosis"]
        if for_triage:
            parts.append(f"- 上次JD诊断: 已完成（匹配度 {diag.get('match_score', 'N/A')}%）")
        else:
            parts.append(f"- 上次JD诊断: {diag.get('jd_title', '')} · 匹配度 {diag.get('match_score', 'N/A')}%")
            gaps = diag.get("gap_skills", [])
            if gaps:
                gap_names = [g.get("name", g) if isinstance(g, dict) else str(g) for g in gaps[:5]]
                parts.append(f"- 技能缺口: {', '.join(gap_names)}")

    # Growth log context
    gc = state.get("growth_context")
    if gc:
        projects = gc.get("projects", [])
        if projects:
            proj_parts = []
            for p in projects[:4]:
                status_map = {"planning": "规划中", "in_progress": "进行中", "completed": "已完成"}
                label = f"「{p['name']}」({status_map.get(p['status'], p['status'])})"
                if p.get("skills"):
                    label += f" 技能:{'/'.join(p['skills'][:3])}"
                proj_parts.append(label)
            parts.append(f"- 正在做的项目: {', '.join(proj_parts)}")
        pursuits = gc.get("pursuits", [])
        if pursuits:
            p_parts = [f"{p['company']} {p['position']}" for p in pursuits[:3] if p.get("company")]
            if p_parts:
                parts.append(f"- 正在追踪的岗位: {', '.join(p_parts)}")

    # Page context
    page = state.get("page_context")
    if page:
        parts.append(f"- 用户当前页面: {page.get('label', '')}（{page.get('route', '')}）")
        page_data = page.get("data", {})
        if page_data:
            for k, v in page_data.items():
                parts.append(f"  · {k}: {v}")

    # Coach memo from prior sessions
    memo = state.get("coach_memo", "")
    if memo:
        parts.append(f"\n教练备忘录（来自之前的对话）:\n{memo}")

    return "\n".join(parts)


# ── Handoff tool factory ─────────────────────────────────────────────────────

def _make_handoff_tool(agent_name: str, description: str, label: str):
    """Create a handoff tool that transfers control to a sub-agent."""

    @tool(f"transfer_to_{agent_name}", description=description)
    def handoff(
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        return Command(
            goto=agent_name,
            update={"messages": [ToolMessage(content=f"转交给{label}", tool_call_id=tool_call_id)]},
        )

    return handoff


# Agent registry: (name, handoff description for triage LLM, Chinese label)
_AGENT_REGISTRY = [
    ("coach_agent", "当用户闲聊、问候、情绪倾诉、职业方向讨论、决策纠结时，转交给成长教练。", "成长教练"),
    ("profile_agent", "当用户需要：简历解析、能力画像查看、技能评分、图谱定位时，转交给画像分析师。", "画像分析师"),
    ("navigator", "当用户需要：岗位搜索、岗位详情、逃生路线、AI冲击分析、转型路径规划时，转交给岗位导航员。", "岗位导航员"),
    ("jd_agent", "当用户需要：JD诊断、技能匹配分析、缺口分析、简历优化建议时，转交给JD诊断师。", "JD诊断师"),
    ("growth_agent", "当用户需要：成长进度查看、学习计划、仪表盘数据、下一步行动推荐时，转交给成长顾问。", "成长顾问"),
    ("practice_agent", "当用户需要：练习面试题、出题、刷题、答题评分、查看题库标签时，转交给练习教练。", "练习教练"),
    ("report_agent", "当用户需要：生成职业发展报告、导出报告、报告润色时，转交给报告撰写师。", "报告撰写师"),
]

HANDOFF_TOOLS = [_make_handoff_tool(name, desc, label) for name, desc, label in _AGENT_REGISTRY]


# ── Triage prompt ─────────────────────────────────────────────────────────────

## NOTE: Triage prompt removed — triage is now a pure router (no LLM chat).
## Chat functionality moved to coach_agent.py.


# ── Intent classifier (LLM-based, lightweight) ──────────────────────────────

import re as _re

_INTENT_CLASSIFY_PROMPT = """判断用户消息应该由哪个专家处理。只输出一个英文单词，不要输出其他任何内容。

分类规则：
- navigator: 明确要求推荐岗位（"推荐""适合我""我能做什么"）、搜索岗位、探索图谱、转型路径、搜招聘信息、搜JD、找工作机会
- jd_agent: 发了一段JD文本、要求诊断匹配度
- profile_agent: 查看/分析画像、技能评估、简历分析
- practice_agent: 面试练习、出题、刷题、模拟面试、面试复盘、练习回顾
- growth_agent: 学习进度、成长数据、下一步行动推荐
- report_agent: 生成/导出职业报告
- coach_agent: 闲聊、问候、情绪倾诉、方向迷茫、职业选择讨论、系统功能咨询、自我介绍、投简历没回复、焦虑

用户消息：{message}
分类："""

_VALID_AGENTS = {"coach_agent", "navigator", "jd_agent", "profile_agent", "practice_agent", "growth_agent", "report_agent"}

# Regex patterns for detecting "search real JD" intent (deterministic, no LLM needed)
# 触发真实JD搜索的模式
# 核心原则：含"搜/找"动词 + 岗位/工作/招聘等名词 → 搜真实JD
_SEARCH_JD_PATTERN = _re.compile(
    r"(帮我|能帮我)?(搜[搜索一下几份]*|找[找几份]*).{0,15}(招聘|岗位|职位|工作机会|JD|职位描述|岗位要求|岗位信息|工作信息)"
    r"|搜[搜一下]*.*?公司"
    r"|[能可]不[能可]帮我搜"
    r"|帮我搜[搜一下]*$"
    r"|搜[搜一下]*看?$"
)

# Cache the classifier LLM instance
_classifier_llm = None


def _get_classifier_llm():
    global _classifier_llm
    if _classifier_llm is None:
        from agent.llm import get_llm_client, get_model
        _classifier_llm = (get_llm_client(timeout=8), get_model("fast"))
    return _classifier_llm


def _detect_intent(text: str) -> tuple[str | None, str]:
    """Classify user intent. Returns (agent_name, tool_hint).

    tool_hint is a string like "search_real_jd" that tells the agent
    which specific tool to use. Empty string means no hint.
    """
    text = text.strip()
    if not text or len(text) < 2:
        return None, ""

    # Fast path 1: JD text detection (long text with JD keywords)
    if len(text) > 100 and any(kw in text for kw in ("岗位职责", "任职要求", "job description", "职位描述", "工作职责", "技能要求")):
        return "jd_agent", ""

    # Fast path 2a: 项目规划请求 → coach_agent (不搜JD)
    if text.startswith("[项目规划请求]") or ("项目规划" in text and "里程碑" in text):
        return "coach_agent", ""

# Fast path 3: 确认语/短回复 → 让 triage 处理（它看得到上下文，能决定 handoff）
    if len(text) <= 6 and _re.search(r"^(好[的啊吧]?|可以[的啊吧!！]?|行[的啊吧]?|嗯[嗯]?|对[的啊]?|是[的啊]?|ok|OK|继续|来吧|开始)$", text):
        return None, ""

    # Fast path 4: 方向迷茫/自我介绍 → coach_agent
    if _re.search(r"不知道.{0,6}(方向|干什么|做什么|选什么|怎么选|发展)|迷茫|该怎么办|我是.{0,8}(学生|专业)", text):
        return "coach_agent", ""

    # Tier 2: Semantic similarity router (fast, no LLM call)
    try:
        from agent.intent_router import classify_intent as _semantic_classify
        agent, hint = _semantic_classify(text)
        if agent is not None or hint:
            logger.info("Semantic router: '%s' → %s (hint=%s)", text[:30], agent, hint)
            return agent, hint
        # Semantic router returned (None, "") — could be chat or unmatched
        # For chat, semantic router returns (None, "") explicitly, so we trust it
        # and skip the LLM classifier to save latency
        # But if the router is not initialized, fall through to LLM
        from agent.intent_router import _initialized as _sr_ready
        if _sr_ready:
            return None, ""
    except Exception as e:
        logger.debug("Semantic router unavailable: %s", e)

    # Tier 3: LLM classifier (fallback for ambiguous cases)
    try:
        client, model = _get_classifier_llm()
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": _INTENT_CLASSIFY_PROMPT.format(message=text[:200])}],
            temperature=0,
            max_tokens=10,
        )
        result = (resp.choices[0].message.content or "").strip().lower()
        for agent in _VALID_AGENTS:
            if agent in result:
                return agent, ""
        return None, ""
    except Exception as e:
        logger.warning("Intent classifier failed: %s", e)
        return None, ""


# ── Graph nodes ───────────────────────────────────────────────────────────────

def _make_triage_node():
    """Create the triage node — PURE ROUTER, never generates user-facing responses.

    Three-tier classification:
    1. Regex fast-path (confirmations, JD text, search keywords, confusion)
    2. Semantic router (embedding similarity, ~93% accuracy)
    3. LLM classifier fallback (for truly ambiguous messages)

    All paths route to an agent. No message goes unrouted — "chat" intent
    goes to coach_agent instead of being handled by triage itself.
    """

    # Build a lookup from agent_name → handoff tool
    handoff_tool_map: dict[str, object] = {}
    for t in HANDOFF_TOOLS:
        agent_name = t.name.replace("transfer_to_", "")
        handoff_tool_map[agent_name] = t

    def _force_handoff(agent_name: str, state: CareerState, tool_hint: str = "") -> dict:
        """Generate a synthetic tool call to force handoff to an agent."""
        import uuid
        state["tool_hint"] = tool_hint
        tool = handoff_tool_map[agent_name]
        return {"messages": [AIMessage(
            content="",
            tool_calls=[{"id": f"route_{uuid.uuid4().hex[:8]}", "name": tool.name, "args": {}}],
        )]}

    def triage_node(state: CareerState) -> dict:
        from langchain_core.messages import HumanMessage

        # Get the last user message
        last_user_msg = ""
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                last_user_msg = msg.content
                break

        # === Confirmation handling (Swarm-style: stay with last agent) ===
        last_agent = state.get("last_active_agent", "")
        if (last_user_msg and len(last_user_msg) <= 6
                and _re.search(r"^(好[的啊吧]?|可以[的啊吧!！]?|行[的啊吧]?|嗯[嗯]?|对[的啊]?|是[的啊]?|ok|OK|继续|来吧|开始)$", last_user_msg)
                and last_agent and last_agent in handoff_tool_map):
            logger.info("Confirmation '%s' → re-route to last agent: %s", last_user_msg, last_agent)
            return _force_handoff(last_agent, state)

        # === Three-tier intent classification ===
        matched_agent, tool_hint = _detect_intent(last_user_msg)

        # _detect_intent returns None for chat/unmatched → route to coach_agent
        target = matched_agent if matched_agent and matched_agent in handoff_tool_map else "coach_agent"

        logger.info("Router: '%s' → %s (hint=%s)", last_user_msg[:50], target, tool_hint)
        return _force_handoff(target, state, tool_hint)

    return triage_node


def _make_agent_node(agent, agent_name: str):
    """Create a graph node that wraps a sub-agent with error handling.

    Filters out handoff artifacts (empty AIMessages with tool_calls,
    ToolMessages from routing) so the sub-agent only sees the clean
    conversation: user messages + actual AI responses.
    """
    from langchain_core.messages import HumanMessage as _HM

    def node(state: CareerState) -> dict:
        context = build_context_summary(state)
        recent = state["messages"][-20:]

        # Clean: only pass user messages and AI messages with real content
        clean = []
        for m in recent:
            if isinstance(m, _HM):
                clean.append(m)
            elif isinstance(m, AIMessage) and m.content and not getattr(m, "tool_calls", None):
                clean.append(m)
            # Skip ToolMessages, empty AIMessages, SystemMessages — these are routing artifacts

        # Extract handoff context: what did triage say before handing off?
        # This helps the sub-agent understand WHY it was called.
        handoff_context = ""
        if len(clean) >= 2:
            last_human = None
            last_ai_before_human = None
            for i in range(len(clean) - 1, -1, -1):
                if isinstance(clean[i], _HM) and last_human is None:
                    last_human = clean[i].content
                elif isinstance(clean[i], AIMessage) and last_human is not None:
                    last_ai_before_human = clean[i].content
                    break
            # If last user message is short (confirmation/follow-up), inject the AI context
            if last_human and len(last_human) <= 20 and last_ai_before_human:
                handoff_context = f"\n\n[调用背景] 教练在上一轮对用户说了：「{last_ai_before_human[:200]}」，用户回复了「{last_human}」表示同意。请据此执行对应的分析任务。"

        # Inject tool hint if present
        tool_hint = state.get("tool_hint", "")
        if tool_hint:
            hint_instructions = {
                "search_real_jd": "用户要求搜索互联网真实招聘信息。你必须使用 search_real_jd 工具搜索，不要用 recommend_jobs 或 search_jobs。如果用户没指定搜什么，根据对话上下文和用户画像中的目标岗位/技能方向来构造搜索关键词（如'C++ 后端开发 招聘'）。",
            }
            hint_text = hint_instructions.get(tool_hint, "")
            if hint_text:
                context += f"\n\n[工具指令] {hint_text}"

        input_msgs = [SystemMessage(content=context + handoff_context)] + clean

        # Inject profile + user_id via ContextVar for jd_agent tools
        _ctx_resets: list[tuple] = []
        if agent_name == "jd_agent":
            from agent.tools.jd_tools import _injected_profile, _injected_user_id
            tok1 = _injected_profile.set(state.get("user_profile"))
            tok2 = _injected_user_id.set(state.get("user_id"))
            _ctx_resets = [(_injected_profile, tok1), (_injected_user_id, tok2)]

        try:
            result = agent.invoke({"messages": input_msgs})
            # Only return NEW messages generated by this agent, not the input messages
            new_messages = result["messages"][len(input_msgs):]
            # Track which agent produced this response (for follow-up routing)
            return {"messages": new_messages, "last_active_agent": agent_name}
        except Exception as e:
            logger.error("Agent '%s' failed: %s", agent_name, e)
            return {
                "messages": [
                    AIMessage(
                        content="抱歉，处理你的请求时遇到了问题。你可以换个方式描述，或稍后再试。"
                    )
                ]
            }
        finally:
            for ctx_var, tok in _ctx_resets:
                ctx_var.reset(tok)

    node.__name__ = agent_name
    return node


# ── Graph construction ────────────────────────────────────────────────────────

def build_supervisor() -> StateGraph:
    """Build and return the compiled Supervisor graph.

    Architecture (pure router pattern):
      START → triage (pure router, no LLM chat)
            → handoff_executor → target agent → END

    All messages get routed to an agent. Triage never generates responses.
    Chat/emotional/exploratory messages go to coach_agent.
    """
    from agent.agents.coach_agent import create_coach_agent
    from agent.agents.growth_agent import create_growth_agent
    from agent.agents.jd_agent import create_jd_agent
    from agent.agents.navigator_agent import create_navigator_agent
    from agent.agents.practice_agent import create_practice_agent
    from agent.agents.profile_agent import create_profile_agent
    from agent.agents.report_agent import create_report_agent

    # Create all agents (including coach)
    agents = {
        "coach_agent": create_coach_agent(),
        "profile_agent": create_profile_agent(),
        "navigator": create_navigator_agent(),
        "jd_agent": create_jd_agent(),
        "growth_agent": create_growth_agent(),
        "practice_agent": create_practice_agent(),
        "report_agent": create_report_agent(),
    }

    graph = StateGraph(CareerState)

    # Nodes
    graph.add_node("triage", _make_triage_node())  # Pure router — no LLM
    graph.add_node("handoff_executor", ToolNode(HANDOFF_TOOLS))
    for name, agent in agents.items():
        graph.add_node(name, _make_agent_node(agent, name))

    # Edges: triage always produces tool calls → handoff_executor → agent → END
    graph.add_edge(START, "triage")
    graph.add_conditional_edges("triage", tools_condition, {
        "tools": "handoff_executor",
        END: END,  # Fallback (should not happen since triage always routes)
    })
    for name in agents:
        graph.add_edge(name, END)

    return graph.compile()
