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

# ── Market signals loader (lazy, cached) ──────────────────────────────────────

_market_signals: dict | None = None
_industry_signals: dict | None = None
_graph_family_map: dict | None = None  # node_id → role_family


def _get_global_market_summary() -> str:
    """Return a compact market summary for all role families (always injected into context).

    This ensures coach always has real data to reference, preventing hallucination
    when no specific career goal is set.
    """
    global _market_signals
    import json
    from pathlib import Path

    if _market_signals is None:
        try:
            data_dir = Path(__file__).resolve().parent.parent / "data"
            _market_signals = json.loads((data_dir / "market_signals.json").read_text(encoding="utf-8"))
        except Exception:
            return ""

    if not _market_signals:
        return ""

    best, good, caution = [], [], []
    for family, sig in _market_signals.items():
        if sig.get("is_proxy"):
            continue
        timing = sig.get("timing", "")
        pct = sig.get("demand_change_pct", 0)
        salary_cagr = sig.get("salary_cagr", 0)
        if timing == "best":
            best.append(f"{family}(需求{pct:+.0f}%，薪资+{salary_cagr:.0f}%/年)")
        elif timing == "good":
            good.append(f"{family}(需求{pct:+.0f}%，薪资+{salary_cagr:.0f}%/年)")
        elif timing == "caution":
            caution.append(f"{family}(需求{pct:+.0f}%)")

    lines = ["- 各CS方向市场时机（系统真实数据，2021→2024年招聘趋势）:"]
    if best:
        lines.append(f"  ✅ 入场好时机: {' / '.join(best)}")
    if good:
        lines.append(f"  ✓ 相对稳健: {' / '.join(good)}")
    if caution:
        lines.append(f"  ⚠️ 岗位收紧（需差异化）: {' / '.join(caution)}")
    lines.append("  [这是系统招聘库的真实数据，用这些数字回答用户，禁止编造其他统计]")

    return "\n".join(lines)


def _get_market_signal_for_node(node_id: str) -> dict | None:
    """Return precomputed market signal + top industries for a graph node_id."""
    global _market_signals, _industry_signals, _graph_family_map
    import json
    from pathlib import Path
    data_dir = Path(__file__).resolve().parent.parent / "data"

    if _market_signals is None:
        try:
            _market_signals = json.loads((data_dir / "market_signals.json").read_text(encoding="utf-8"))
        except Exception:
            _market_signals = {}
    if _industry_signals is None:
        try:
            _industry_signals = json.loads((data_dir / "industry_signals.json").read_text(encoding="utf-8"))
        except Exception:
            _industry_signals = {}
    if _graph_family_map is None:
        try:
            nodes = json.loads((data_dir / "graph.json").read_text(encoding="utf-8")).get("nodes", [])
            _graph_family_map = {n["node_id"]: n.get("role_family", "") for n in nodes}
        except Exception:
            _graph_family_map = {}

    role_family = _graph_family_map.get(node_id, "")
    if not role_family:
        return None
    sig = _market_signals.get(role_family)
    if sig:
        # Merge top industries from separate file
        sig = dict(sig)
        sig["top_industries"] = _industry_signals.get(role_family, [])[:3]
    return sig


# ── Context summary builder ───────────────────────────────────────────────────

def build_context_summary(state: CareerState, for_triage: bool = False) -> str:
    """Create a structured summary from shared state.

    Args:
        state: The shared CareerState.
        for_triage: If True, omit detailed skill/profile data to prevent
                    triage from fabricating data-dependent answers.
    """
    parts = ["当前用户状态："]

    # Always inject global market summary so coach has real data regardless of career goal
    if not for_triage:
        market_summary = _get_global_market_summary()
        if market_summary:
            parts.append(market_summary)

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
        # Resume projects — inject so coach doesn't ask "what projects have you done"
        if not for_triage:
            resume_projects = profile.get("projects", [])
            if resume_projects:
                proj_parts = []
                for p in resume_projects[:3]:
                    if isinstance(p, dict):
                        name = p.get("name", "")
                        desc = p.get("description", "")
                        if name:
                            proj_parts.append(f"「{name}」{desc[:60] if desc else ''}")
                    elif p:
                        proj_parts.append(str(p)[:60])
                if proj_parts:
                    parts.append(f"- 简历项目: {' / '.join(proj_parts)}")
        # Career preferences
        prefs = profile.get("preferences", {})
        if not for_triage:
            if prefs and any(prefs.values()):
                pref_labels = {
                    "work_style": {"tech": "深挖技术", "product": "做产品", "data": "分析数据", "management": "带团队"},
                    "value_priority": {"growth": "技术成长", "stability": "薪资稳定", "balance": "工作生活平衡", "innovation": "行业前景"},
                    "ai_attitude": {"do_ai": "拥抱AI工具", "avoid_ai": "找AI替代不了的", "no_preference": "看机会"},
                    "company_type": {"big_tech": "大厂", "growing": "成长型公司", "startup": "初创", "state_owned": "国企"},
                    "work_intensity": {"high": "可以拼", "moderate": "偶尔加班", "low": "准时下班"},
                    "current_stage": {"lost": "方向迷茫", "know_gap": "有方向但技能不足", "ready": "技能够但找不到机会", "not_started": "刚开始考虑就业"},
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
                # No preferences filled — remind coach to prompt user at right moment
                parts.append("- 就业意愿: 未填写（如对话中合适，引导用户去画像页填写就业意愿问卷）")
    else:
        parts.append("- 画像: 未建立（建议先上传简历）")

    if state.get("career_goal"):
        goal = state["career_goal"]
        parts.append(f"- 目标岗位: {goal.get('label', '未知')}")
        if goal.get("zone"):
            zone_names = {"safe": "安全区", "thrive": "成长区", "transition": "转型区", "danger": "风险区"}
            parts.append(f"- 目标区域: {zone_names.get(goal['zone'], goal['zone'])}")
        # Inject real market signal for target direction
        if not for_triage:
            target_node = goal.get("target_node_id", "")
            sig = _get_market_signal_for_node(target_node) if target_node else None
            if sig and sig.get("timing") not in ("no_data", None):
                timing_icons = {"best": "✅", "good": "✓", "neutral": "→", "caution": "⚠️"}
                icon = timing_icons.get(sig["timing"], "")
                parts.append(
                    f"- 目标方向市场动态: {icon} {sig.get('timing_label','')} — {sig.get('timing_reason','')}"
                )
                demand = sig.get("demand_label", "")
                salary = sig.get("salary_label", "")
                ai_info = sig.get("ai_label", "")
                if demand:
                    parts.append(f"  · 需求: {demand}（{sig.get('demand_change_pct',0):+.0f}%，{sig.get('baseline_year')}→{sig.get('compare_year')}）")
                if salary:
                    parts.append(f"  · 薪资: {salary}")
                if ai_info:
                    parts.append(f"  · AI渗透: {ai_info}")
                # Top industries
                top_inds = sig.get("top_industries", [])
                if top_inds:
                    ind_names = " | ".join(
                        i["industry"][:10] for i in top_inds[:3] if i.get("industry")
                    )
                    parts.append(f"  · 主要招聘行业: {ind_names}")
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
                # JDService returns {skill, priority, match_delta}; legacy may use {name}
                gap_names = []
                for g in gaps[:5]:
                    if isinstance(g, dict):
                        name = g.get("skill") or g.get("name") or ""
                        if name:
                            gap_names.append(str(name))
                    elif g:
                        gap_names.append(str(g))
                if gap_names:
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
        note_count = gc.get("learning_notes_count", 0)
        latest_note = gc.get("latest_note_title")
        if note_count > 0:
            note_hint = f"- 学习笔记: {note_count}条"
            if latest_note:
                note_hint += f"（最新：{latest_note}）"
            note_hint += " | 可调用 get_learning_notes 查询详情"
            parts.append(note_hint)

    # Page context
    page = state.get("page_context")
    if page:
        parts.append(f"- 用户当前页面: {page.get('label', '')}（{page.get('route', '')}）")
        page_data = page.get("data", {})
        if page_data:
            for k, v in page_data.items():
                parts.append(f"  · {k}: {v}")


    # Action plan progress (from ActionPlanV2)
    ap_ctx = state.get("action_plan_context")
    if ap_ctx and not for_triage:
        ap_stages = ap_ctx.get("stages", [])
        if ap_stages:
            parts.append("- 成长计划进度:")
            for s in ap_stages:
                done, total = s.get("done", 0), s.get("total", 0)
                label = s.get("label", f"阶段{s.get('stage')}")
                status = "✅已完成" if done == total and total > 0 else f"{done}/{total}"
                parts.append(f"  · {label}: {status}")
                pending = s.get("pending_preview", [])
                if pending:
                    parts.append(f"    待完成: {'、'.join(pending)}")

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
    ("navigator", "当用户需要：岗位图谱方向分析、逃生路线、AI冲击分析、转型路径规划时，转交给方向顾问。", "方向顾问"),
    ("search_agent", "当用户需要：搜索真实招聘 JD、找校招信息、按公司/技术方向搜岗位时，转交给岗位搜索员。", "岗位搜索员"),
    ("jd_agent", "当用户需要：JD诊断、技能匹配分析、缺口分析、简历优化建议时，转交给JD诊断师。", "JD诊断师"),
    ("growth_agent", "当用户需要：成长进度查看、学习计划、仪表盘数据、下一步行动推荐时，转交给成长顾问。", "成长顾问"),
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
- growth_agent: 学习进度、成长数据、下一步行动推荐
- coach_agent: 闲聊、问候、情绪倾诉、方向迷茫、职业选择讨论、系统功能咨询、自我介绍、投简历没回复、焦虑

用户消息：{message}
分类："""

_VALID_AGENTS = {"coach_agent", "navigator", "search_agent", "jd_agent", "profile_agent", "growth_agent"}

# Regex patterns for detecting "search real JD" intent (deterministic, no LLM needed)
# 触发真实JD搜索的模式
# 核心原则：含"搜/找"动词 + 岗位/工作/招聘等名词 → 搜真实JD
_SEARCH_JD_PATTERN = _re.compile(
    # 动词 + 泛化对象（招聘/岗位/职位/工作/JD）
    r"(帮我|能帮我)?(搜[搜索一下几份]*|找[找几份]*).{0,20}(招聘|岗位|职位|工作|JD|职位描述|岗位要求|岗位信息|工作信息|机会)"
    # 动词 + 具体岗位方向（后端/前端/算法/开发/工程师）
    r"|(帮我|能帮我)?(搜[搜索一下几份]*|找[找几份]*).{0,20}(后端|前端|全栈|算法|开发|工程师|实习|校招|测试|运维|数据|ai|llm|架构)"
    # 动词 + 公司名（搜xx公司）
    r"|搜[搜一下]*.*?公司"
    # 省略宾语的求助
    r"|[能可]不[能可]帮我搜"
    r"|帮我搜[搜一下]*$"
    r"|搜[搜一下]*看?$",
    _re.IGNORECASE,
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
    _JD_KEYWORDS = (
        "岗位职责", "任职要求", "job description", "职位描述", "工作职责", "技能要求",
        "岗位描述", "岗位要求", "任职资格", "职责描述", "职位要求", "工作职责",
        "加分项", "基本要求", "招聘要求", "薪资待遇", "岗位详情", "校园招聘",
        "必须具备", "有一定了解", "工作地点", "base 地",
    )
    if len(text) > 100 and any(kw in text for kw in _JD_KEYWORDS):
        return "jd_agent", ""
    # Explicit "诊断" intent + JD indicator (even if keywords above don't match)
    if ("诊断" in text[:30] or "分析" in text[:30]) and len(text) > 200 and "JD" in text[:50]:
        return "jd_agent", ""

    # Fast path 2: Search real JD intent (deterministic regex, bypass broken semantic router)
    # 触发"搜索真实招聘"必须有两个条件：动词（搜/找）+ 岗位类名词
    # → 路由到 search_agent (workflow，强制调 search_real_jd 工具)
    if _SEARCH_JD_PATTERN.search(text):
        return "search_agent", ""

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
        if agent_name == "growth_agent":
            from agent.tools.growth_tools import _injected_user_id as _growth_uid
            tok_gu = _growth_uid.set(state.get("user_id"))
            _ctx_resets = [(_growth_uid, tok_gu)]
        if agent_name == "jd_agent":
            from agent.tools.jd_tools import _injected_profile, _injected_user_id
            tok1 = _injected_profile.set(state.get("user_profile"))
            tok2 = _injected_user_id.set(state.get("user_id"))
            _ctx_resets = [(_injected_profile, tok1), (_injected_user_id, tok2)]

        # Inject profile/goal for search_real_jd (used by navigator + coach + search_agent)
        if agent_name in ("navigator", "coach_agent", "search_agent"):
            from agent.tools.search_tools import (
                _injected_profile_for_search, _injected_goal_for_search,
            )
            tok_sp = _injected_profile_for_search.set(state.get("user_profile"))
            tok_sg = _injected_goal_for_search.set(state.get("career_goal"))
            _ctx_resets.extend([
                (_injected_profile_for_search, tok_sp),
                (_injected_goal_for_search, tok_sg),
            ])

        try:
            # Guard: cap message history to prevent memory blow-up and infinite loops
            _MAX_MSGS = 60
            if len(input_msgs) > _MAX_MSGS:
                logger.warning(
                    "Agent '%s' message history too long (%d), truncating to %d",
                    agent_name, len(input_msgs), _MAX_MSGS,
                )
                # Keep system message + last (_MAX_MSGS - 1) messages
                input_msgs = input_msgs[:1] + input_msgs[-(  _MAX_MSGS - 1):]

            result = agent.invoke({"messages": input_msgs})
            # Only return NEW messages generated by this agent, not the input messages
            new_messages = result["messages"][len(input_msgs):]
            # Sanity check: if agent produced suspiciously many messages, something looped
            if len(new_messages) > 20:
                logger.warning(
                    "Agent '%s' produced %d messages (possible loop), truncating",
                    agent_name, len(new_messages),
                )
                new_messages = new_messages[:20]
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
    from agent.agents.profile_agent import create_profile_agent
    from agent.agents.search_agent import create_search_agent

    agents = {
        "coach_agent": create_coach_agent(),
        "profile_agent": create_profile_agent(),
        "navigator": create_navigator_agent(),
        "search_agent": create_search_agent(),
        "jd_agent": create_jd_agent(),
        "growth_agent": create_growth_agent(),
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
