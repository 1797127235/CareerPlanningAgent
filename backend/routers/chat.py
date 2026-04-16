"""SSE chat endpoint — streams Supervisor multi-agent responses + session persistence."""
from __future__ import annotations

import json
import logging
import re
import threading

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.auth import get_current_user
from backend.db import get_db
from backend.db_models import (
    CareerGoal,
    ChatMessage,
    ChatSession,
    CoachResult,
    InterviewRecord,
    JDDiagnosis,
    JobApplication,
    Profile,
    ProjectRecord,
    Report,
    User,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_supervisor = None

# ── Market card extraction ────────────────────────────────────────────────────

_market_signals_for_cards: dict | None = None

def _extract_market_cards(text: str) -> list[dict]:
    """Detect market direction mentions in coach response, return signal cards for frontend.

    Emitted as market_cards SSE event so frontend can render inline data cards.
    Only fires for coach_agent responses that reference market directions.
    """
    global _market_signals_for_cards
    if _market_signals_for_cards is None:
        import json as _json
        from pathlib import Path as _Path
        try:
            _data = _Path(__file__).resolve().parent.parent.parent / "data" / "market_signals.json"
            _market_signals_for_cards = _json.loads(_data.read_text(encoding="utf-8"))
        except Exception:
            _market_signals_for_cards = {}

    signals = _market_signals_for_cards
    if not signals:
        return []

    # Node ID → short readable label for card preview
    _NODE_LABELS: dict[str, str] = {
        "java": "Java", "python": "Python", "golang": "Go", "cpp": "C++", "rust": "Rust",
        "frontend": "前端", "full-stack": "全栈", "android": "Android", "ios": "iOS",
        "flutter": "Flutter", "react-native": "RN", "ai-engineer": "AI工程师",
        "machine-learning": "ML", "ai-data-scientist": "AI数据", "ai-agents": "AI Agent",
        "mlops": "MLOps", "ml-architect": "ML架构", "algorithm-engineer": "算法",
        "data-analyst": "数据分析", "data-engineer": "数据工程", "bi-analyst": "BI",
        "postgresql-dba": "DBA", "data-architect": "数据架构",
        "devops": "DevOps", "devsecops": "DevSecOps", "cloud-architect": "云架构",
        "game-developer": "游戏开发", "server-side-game-developer": "游戏服务端",
        "cyber-security": "网络安全", "ai-red-teaming": "AI红队", "security-architect": "安全架构",
        "qa": "测试", "qa-lead": "测试负责人",
        "product-manager": "产品经理", "engineering-manager": "技术管理", "cto": "CTO",
        "search-engine-engineer": "搜索引擎", "storage-database-kernel": "存储内核",
        "infrastructure-engineer": "基础设施", "software-architect": "软件架构",
    }

    # Keyword aliases: family → list of phrases to look for in text
    # 规则：
    #   - 中文短语：用子串匹配（中文没有词边界概念），必须是能唯一识别方向的精确短语
    #     ❌ 不要裸 "数据"（会命中"数据库"/"数据结构"）
    #     ❌ 不要裸 "游戏"（会命中"小游戏"等无关语境）
    #   - 英文/数字关键词：用词边界正则，避免子串误匹配
    #     ❌ "React" 会子串命中 "Reactor"、"UE" 会命中 "cue"
    #     ✅ 用 "React.js" 或用词边界 r"\bReact\b"
    _ALIASES: dict[str, list[str]] = {
        "AI/ML":       ["AI/ML", "AI方向", "AI 方向", "人工智能", "机器学习", "深度学习", "大模型", "LLM", "AIGC"],
        "后端开发":    ["后端开发", "后端方向", "服务端开发", "后台开发", "Java", "Python", "Golang", "Go语言", "SpringBoot"],
        "系统开发":    ["系统开发", "系统软件", "底层开发", "内核开发", "基础架构", "中间件", "C++", "Rust"],
        "前端开发":    ["前端开发", "前端方向", "前端工程", "Vue.js", "React.js", "Next.js", "Angular", "TypeScript"],
        "数据":        ["数据方向", "数据分析", "数据工程", "大数据", "数仓", "数据仓库", "数据科学", "BI"],
        "移动开发":    ["移动开发", "移动端", "App开发", "Android", "iOS", "Flutter"],
        "游戏开发":    ["游戏开发", "游戏客户端", "游戏引擎", "Unity", "UE4", "UE5"],
        "运维/DevOps": ["运维开发", "运维方向", "DevOps", "云原生", "Kubernetes", "k8s", "SRE"],
        "安全":        ["安全方向", "网络安全", "信息安全", "渗透测试", "红蓝对抗"],
        "质量保障":    ["质量保障", "测试开发", "自动化测试"],
        "产品":        ["产品方向", "产品经理", "产品设计"],
        "管理":        ["技术管理", "工程管理", "CTO"],
    }

    # 纯 ASCII 关键词识别（允许 + # . / -），用于决定是否走词边界正则
    _ASCII_ONLY = re.compile(r"^[A-Za-z0-9+#./\- ]+$")

    def _kw_hit(kw: str, body: str) -> bool:
        """Check if keyword appears in body.
        - ASCII-only keywords: word-boundary match (avoids "React" hitting "Reactor")
        - Chinese/mixed: literal substring (Chinese has no word boundaries)
        """
        if _ASCII_ONLY.match(kw):
            pat = rf"(?<![A-Za-z0-9]){re.escape(kw.strip())}(?![A-Za-z0-9])"
            return bool(re.search(pat, body))
        return kw in body

    cards = []
    seen: set[str] = set()

    for family, aliases in _ALIASES.items():
        if family in seen or family not in signals:
            continue
        sig = signals[family]
        if sig.get("is_proxy"):
            continue

        # ⚠️ 禁止裸 family name 子串匹配（family="数据" 会命中"数据库"）
        # 只允许精确别名命中
        matched = any(_kw_hit(kw, text) for kw in aliases)
        if not matched:
            continue

        node_ids = sig.get("node_ids", [])
        role_examples = [_NODE_LABELS.get(n, n) for n in node_ids[:3]]
        cards.append({
            "family": family,
            "timing": sig.get("timing"),
            "timing_label": sig.get("timing_label", ""),
            "demand_change_pct": sig.get("demand_change_pct", 0),
            "salary_cagr": sig.get("salary_cagr", 0),
            "node_id": node_ids[0] if node_ids else None,
            "role_examples": role_examples,
        })
        seen.add(family)

    return cards[:4]  # Cap at 4 to avoid UI clutter


_graph_family_map_for_cards: dict | None = None

def _get_card_for_node(node_id: str) -> dict | None:
    """Get a market signal card for a specific graph node_id."""
    global _market_signals_for_cards, _graph_family_map_for_cards
    import json as _json2
    from pathlib import Path as _Path2

    if _graph_family_map_for_cards is None:
        try:
            _gdata = _Path2(__file__).resolve().parent.parent.parent / "data" / "graph.json"
            nodes = _json2.loads(_gdata.read_text(encoding="utf-8")).get("nodes", [])
            _graph_family_map_for_cards = {n["node_id"]: n.get("role_family", "") for n in nodes}
        except Exception:
            _graph_family_map_for_cards = {}

    signals = _market_signals_for_cards or {}
    role_family = (_graph_family_map_for_cards or {}).get(node_id, "")
    if not role_family or role_family not in signals:
        return None

    sig = signals[role_family]
    if sig.get("is_proxy"):
        # Use the proxy's real family data
        proxy_family = sig.get("proxy_family", "")
        if proxy_family and proxy_family in signals:
            sig = signals[proxy_family]
            role_family = proxy_family

    node_ids = sig.get("node_ids", [])
    _NODE_LABELS_REF = {
        "java": "Java", "python": "Python", "golang": "Go", "cpp": "C++", "rust": "Rust",
        "frontend": "前端", "full-stack": "全栈", "android": "Android", "ios": "iOS",
        "flutter": "Flutter", "react-native": "RN", "ai-engineer": "AI工程师",
        "machine-learning": "ML", "ai-data-scientist": "AI数据", "ai-agents": "AI Agent",
        "mlops": "MLOps", "algorithm-engineer": "算法",
        "data-analyst": "数据分析", "data-engineer": "数据工程",
        "devops": "DevOps", "cloud-architect": "云架构",
        "game-developer": "游戏开发", "cyber-security": "网络安全",
        "qa": "测试", "product-manager": "产品经理", "engineering-manager": "技术管理",
    }
    role_examples = [_NODE_LABELS_REF.get(n, n) for n in node_ids[:3]]

    return {
        "family": role_family,
        "timing": sig.get("timing"),
        "timing_label": sig.get("timing_label", ""),
        "demand_change_pct": sig.get("demand_change_pct", 0),
        "salary_cagr": sig.get("salary_cagr", 0),
        "node_id": node_id,  # Keep original node_id for accurate navigation
        "role_examples": role_examples,
    }


def _get_supervisor():
    global _supervisor
    if _supervisor is None:
        from agent.supervisor import build_supervisor

        _supervisor = build_supervisor()
    return _supervisor


class PageContext(BaseModel):
    route: str = ""
    label: str = ""
    data: dict = {}


class ChatRequest(BaseModel):
    message: str
    session_id: int | None = None
    history: list[dict] = []
    page_context: PageContext | None = None


def _hydrate_state(user: User, db: Session) -> dict:
    """Build a rich initial CareerState from the user's DB data."""
    from backend.services.stage import compute_stage

    state: dict = {
        "user_id": user.id,
        "profile_id": None,
        "user_profile": None,
        "career_goal": None,
        "current_node_id": None,
        "user_stage": "no_profile",
        "last_diagnosis": None,
    }

    # 1. Active profile
    profile = (
        db.query(Profile)
        .filter_by(user_id=user.id)
        .order_by(Profile.updated_at.desc())
        .first()
    )
    if profile:
        state["profile_id"] = profile.id
        try:
            state["user_profile"] = json.loads(profile.profile_json or "{}")
        except (json.JSONDecodeError, TypeError):
            state["user_profile"] = {}

    # 2. Career goal — exclude placeholder goals (target_node_id="")
    goal = (
        db.query(CareerGoal)
        .filter(
            CareerGoal.user_id == user.id,
            CareerGoal.is_active == True,  # noqa: E712
            CareerGoal.target_node_id != "",
        )
        .order_by(CareerGoal.set_at.desc())
        .first()
    )
    if goal:
        state["career_goal"] = {
            "label": goal.target_label,
            "node_id": goal.target_node_id,
            "zone": goal.target_zone,
        }
        state["current_node_id"] = goal.target_node_id

    # 3. Latest JD diagnosis
    latest_jd = (
        db.query(JDDiagnosis)
        .filter_by(user_id=user.id)
        .order_by(JDDiagnosis.created_at.desc())
        .first()
    )
    if latest_jd:
        try:
            result = json.loads(latest_jd.result_json or "{}")
            state["last_diagnosis"] = {
                "match_score": latest_jd.match_score,
                "jd_title": latest_jd.jd_title,
                "gap_skills": result.get("gap_skills", []),
            }
        except (json.JSONDecodeError, TypeError):
            pass

    # 4. Compute journey stage
    profile_count = db.query(func.count(Profile.id)).filter_by(user_id=user.id).scalar() or 0
    jd_count = db.query(func.count(JDDiagnosis.id)).filter_by(user_id=user.id).scalar() or 0
    project_count = db.query(func.count(ProjectRecord.id)).filter_by(user_id=user.id).scalar() or 0
    app_count = db.query(func.count(JobApplication.id)).filter_by(user_id=user.id).scalar() or 0
    interview_count = db.query(func.count(InterviewRecord.id)).filter_by(user_id=user.id).scalar() or 0
    activity_count = project_count + app_count + interview_count
    report_count = db.query(func.count(Report.id)).filter_by(user_id=user.id).scalar() or 0

    state["user_stage"] = compute_stage(profile_count, jd_count, activity_count, report_count)

    # 5. Growth coach state
    state["coach_memo"] = ""
    state["page_context"] = None
    state["tool_hint"] = ""
    state["last_active_agent"] = ""
    if profile:
        state["coach_memo"] = profile.coach_memo or ""

    # 6. Growth log context — lightweight metadata only (details via tools)
    try:
        projects = (
            db.query(ProjectRecord)
            .filter_by(user_id=user.id)
            .order_by(ProjectRecord.created_at.desc())
            .limit(5)
            .all()
        )
        pursuits = (
            db.query(JobApplication)
            .filter(
                JobApplication.user_id == user.id,
                ~JobApplication.status.in_(["withdrawn", "rejected"]),
            )
            .order_by(JobApplication.created_at.desc())
            .limit(5)
            .all()
        )
        state["growth_context"] = {
            "projects": [
                {
                    "name": p.name,
                    "status": p.status,
                    "skills": (p.skills_used or [])[:5],
                    "description": (p.description or "")[:80],
                }
                for p in projects
            ],
            "pursuits": [
                {
                    "company": a.company or "",
                    "position": a.position or "",
                    "status": a.status,
                }
                for a in pursuits
            ],
        }
    except Exception:
        logger.exception("Failed to load growth context")
        state["growth_context"] = None

    # 7. Action plan context — current stage tasks from ActionPlanV2
    state["action_plan_context"] = None
    if profile:
        try:
            from backend.db_models import ActionPlanV2, ActionProgress
            latest_plan = (
                db.query(ActionPlanV2)
                .filter(ActionPlanV2.profile_id == profile.id)
                .order_by(ActionPlanV2.generated_at.desc())
                .first()
            )
            if latest_plan:
                report_key = latest_plan.report_key
                stages = (
                    db.query(ActionPlanV2)
                    .filter(ActionPlanV2.profile_id == profile.id, ActionPlanV2.report_key == report_key)
                    .order_by(ActionPlanV2.stage)
                    .all()
                )
                progress = (
                    db.query(ActionProgress)
                    .filter(ActionProgress.profile_id == profile.id, ActionProgress.report_key == report_key)
                    .first()
                )
                checked = progress.checked if progress else {}
                plan_stages = []
                for s in stages:
                    content = s.content if isinstance(s.content, dict) else json.loads(s.content or "{}")
                    items = content.get("items", [])
                    total = len(items)
                    done = sum(1 for it in items if checked.get(it.get("id", "")))
                    pending = [it.get("text", "")[:40] for it in items if not checked.get(it.get("id", ""))]
                    plan_stages.append({
                        "stage": content.get("stage", s.stage),
                        "label": content.get("label", ""),
                        "total": total,
                        "done": done,
                        "pending_preview": pending[:2],
                    })
                state["action_plan_context"] = {"stages": plan_stages}
        except Exception:
            logger.debug("Failed to load action plan context", exc_info=True)

    return state


# ── Graph node lookup (lazy, shared with greeting) ───────────────────────────
_CHAT_GRAPH_NODES: dict | None = None
_CHAT_GRAPH_MTIME: float = 0.0


def _get_graph_nodes_for_chat() -> dict:
    """Lightweight graph node cache for chat.py — avoids importing profiles module."""
    global _CHAT_GRAPH_NODES, _CHAT_GRAPH_MTIME
    import os
    graph_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "graph.json"
    )
    try:
        mtime = os.path.getmtime(graph_path)
    except OSError:
        mtime = 0.0
    if _CHAT_GRAPH_NODES is None or mtime != _CHAT_GRAPH_MTIME:
        try:
            with open(graph_path, "r", encoding="utf-8") as f:
                nodes = json.load(f).get("nodes", [])
            _CHAT_GRAPH_NODES = {n["node_id"]: n for n in nodes}
            _CHAT_GRAPH_MTIME = mtime
        except Exception:
            _CHAT_GRAPH_NODES = {}
    return _CHAT_GRAPH_NODES or {}


# ── Growth Coach greeting ────────────────────────────────────────────────────

def _build_greeting(user: User, db: Session) -> dict:
    """Build a stage-aware greeting + dynamic action chips for the chat panel."""
    from backend.services.stage import compute_stage

    # Gather user state
    profile = (
        db.query(Profile)
        .filter_by(user_id=user.id)
        .order_by(Profile.updated_at.desc())
        .first()
    )
    profile_name = "同学"
    skill_count = 0
    profile_data: dict = {}
    if profile:
        profile_name = profile.name or "同学"
        try:
            profile_data = json.loads(profile.profile_json or "{}")
        except (json.JSONDecodeError, TypeError):
            pass
        skill_count = len(profile_data.get("skills", []))

    goal = (
        db.query(CareerGoal)
        .filter(
            CareerGoal.user_id == user.id,
            CareerGoal.is_active == True,  # noqa: E712
            CareerGoal.target_node_id != "",
        )
        .order_by(CareerGoal.set_at.desc())
        .first()
    )

    profile_count = db.query(func.count(Profile.id)).filter_by(user_id=user.id).scalar() or 0
    jd_count = db.query(func.count(JDDiagnosis.id)).filter_by(user_id=user.id).scalar() or 0
    project_count = db.query(func.count(ProjectRecord.id)).filter_by(user_id=user.id).scalar() or 0
    app_count = db.query(func.count(JobApplication.id)).filter_by(user_id=user.id).scalar() or 0
    interview_count = db.query(func.count(InterviewRecord.id)).filter_by(user_id=user.id).scalar() or 0
    activity_count = project_count + app_count + interview_count
    report_count = db.query(func.count(Report.id)).filter_by(user_id=user.id).scalar() or 0

    stage = compute_stage(profile_count, jd_count, activity_count, report_count)

    # Guard: auto-created empty profiles inflate profile_count to 1 even with no content.
    # A profile record with zero skills AND no name AND no raw_text is effectively "no profile".
    # Override stage so the greeting doesn't say "画像建好了！0项技能".
    if stage == "has_profile":
        has_real_content = (
            skill_count > 0
            or bool(profile_data.get("name", "").strip())
            or bool(profile_data.get("raw_text", ""))
            or len(profile_data.get("knowledge_areas", [])) > 0
            or len(profile_data.get("projects", [])) > 0
        )
        if not has_real_content:
            stage = "no_profile"

    # Detect "processing" state: profile has skills but background graph-location
    # thread hasn't finished yet (cached_recs_json is still empty '{}').
    # Don't show "go explore directions" greeting — recommendations aren't ready.
    recs_ready = False
    if stage == "has_profile" and profile:
        try:
            cached = json.loads(profile.cached_recs_json or "{}")
            # Structure: {"hash": "...", "data": {"recommendations": [...]}}
            recs_ready = bool(cached.get("data", {}).get("recommendations"))
        except (json.JSONDecodeError, TypeError):
            recs_ready = False

    # Latest JD diagnosis info
    latest_jd_score = None
    gap_count = 0
    if jd_count > 0:
        latest_jd = (
            db.query(JDDiagnosis)
            .filter_by(user_id=user.id)
            .order_by(JDDiagnosis.created_at.desc())
            .first()
        )
        if latest_jd:
            latest_jd_score = latest_jd.match_score
            try:
                result = json.loads(latest_jd.result_json or "{}")
                gap_count = len(result.get("gap_skills", []))
            except (json.JSONDecodeError, TypeError):
                pass

    # 学习路径已砍 — learning_pct 默认 0，不再参与 greeting 文案（stage 判断仍保留）
    learning_pct = 0

    # Build greeting and chips per stage
    greeting = ""
    chips: list[dict] = []

    if stage == "no_profile":
        greeting = (
            f"嗨！我是你的职业成长教练。\n\n"
            f"我们先从了解你开始——上传一份简历，我帮你做能力画像和方向分析。"
        )
        chips = [
            {"label": "这个系统能做什么？", "prompt": "介绍一下你的功能"},
            {"label": "我是计算机专业学生", "prompt": "我是计算机专业的大三学生，不知道该找什么方向的工作"},
            {"label": "前端和后端怎么选", "prompt": "前端和后端该怎么选？"},
        ]

    elif stage == "has_profile" and not goal:
        if not recs_ready:
            # ── Processing state: background graph-location not done yet ──────
            # Don't say "go explore directions" — recommendations aren't ready.
            greeting = (
                f"简历解析完成，{profile_name}！我正在分析你的技能背景并匹配最适合的方向，"
                f"通常需要十几秒——稍后刷新就能看到结果。\n\n"
                f"你也可以先告诉我你感兴趣的方向，我来帮你分析。"
            )
            chips = [
                {"label": "我对后端开发感兴趣", "prompt": "我对后端开发方向感兴趣，帮我分析适不适合"},
                {"label": "我对AI/大模型感兴趣", "prompt": "我对AI和大模型方向感兴趣，帮我分析"},
                {"label": "帮我解释这个系统能做什么", "prompt": "介绍一下这个系统能帮我做什么"},
            ]
        else:
            # A/B 类用户区分：简历里有明确求职意向 → B 类（目的型），否则 → A 类（探索型）
            job_target = profile_data.get("job_target", "").strip()
            if job_target:
                # B 类：已有方向意向，帮他分析这个具体方向
                greeting = (
                    f"画像建好了，{profile_name}！我看到你的求职意向是「{job_target}」。\n\n"
                    f"先别急着定目标——让我帮你分析这个方向的真实市场情况和你的差距，看清楚再做决定。"
                )
                chips = [
                    {"label": f"分析「{job_target}」方向", "prompt": f"帮我深入分析{job_target}这个方向，市场需求、薪资范围和我的差距"},
                    {"label": "这个方向竞争激烈吗", "prompt": f"{job_target}这个方向的就业竞争情况怎么样？"},
                    {"label": "还有哪些相似方向", "prompt": f"和{job_target}相似或相关的职业方向有哪些，帮我对比一下"},
                ]
            else:
                # A 类：分析已就绪，主动出牌——直接呈现顶部推荐 + zone 信号
                # Read top recommendation from cache
                top_rec = None
                top_zone = None
                top_entry_barrier = None
                try:
                    cached = json.loads(profile.cached_recs_json or "{}")
                    # Structure: {"hash": "...", "data": {"recommendations": [...]}}
                    recs_list = cached.get("data", {}).get("recommendations", [])
                    if recs_list:
                        top_rec = recs_list[0]
                        # Get zone & entry_barrier from graph node
                        graph_nodes = _get_graph_nodes_for_chat()
                        node_data = graph_nodes.get(top_rec.get("role_id", ""), {})
                        top_zone = node_data.get("zone", "")
                        top_entry_barrier = node_data.get("entry_barrier", "")
                except (json.JSONDecodeError, TypeError):
                    pass

                if top_rec:
                    top_label = top_rec.get("label") or top_rec.get("role_id", "")
                    top_pct = top_rec.get("affinity_pct", 0)

                    # Compose zone-aware signal line
                    if top_zone == "danger":
                        signal = (
                            f"不过我要提前跟你说一件事：这个方向目前受 AI 自动化冲击比较大，"
                            f"市场需求在收缩。你想先听听我的分析，还是也看看相近的替代方向？"
                        )
                        chips = [
                            {"label": f"告诉我「{top_label}」的具体风险", "prompt": f"帮我分析{top_label}这个方向的AI替代风险和市场现状"},
                            {"label": "有没有更稳的替代方向", "prompt": f"和{top_label}相近但更有前景的方向有哪些？"},
                            {"label": "我就想做这个，怎么出圈", "prompt": f"如果坚持做{top_label}，怎么在竞争中建立差异化？"},
                        ]
                    elif top_zone == "transition":
                        signal = (
                            f"这个方向的市场正在转型期——需求结构在变化，"
                            f"了解清楚再决定会更稳妥。你想深入聊聊吗？"
                        )
                        chips = [
                            {"label": f"「{top_label}」方向怎么转型", "prompt": f"{top_label}这个方向市场正在如何转变，我该怎么准备？"},
                            {"label": "告诉我为什么推荐这个", "prompt": f"为什么「{top_label}」最匹配我？帮我分析原因"},
                            {"label": "还有哪些更稳的方向", "prompt": "有没有比这个更稳定的方向值得考虑？"},
                        ]
                    elif top_entry_barrier in ("low",):
                        signal = (
                            f"这个方向进入门槛相对低，竞争者也多——"
                            f"你想了解一下怎么在里面建立差异化吗？"
                        )
                        chips = [
                            {"label": f"告诉我为什么推荐「{top_label}」", "prompt": f"为什么「{top_label}」最匹配我？帮我分析"},
                            {"label": "怎么在这个方向出圈", "prompt": f"{top_label}方向竞争激烈，怎么让我的背景脱颖而出？"},
                            {"label": "有没有竞争更少的方向", "prompt": "有没有需求不错但竞争相对没那么大的方向？"},
                        ]
                    else:
                        # Safe/leverage + medium/high barrier: positive recommendation
                        signal = f"你怎么看这个方向？可以告诉我你的想法，我们来聊聊。"
                        chips = [
                            {"label": f"告诉我为什么推荐「{top_label}」", "prompt": f"为什么「{top_label}」最匹配我？详细分析一下"},
                            {"label": "看看其他推荐方向", "prompt": "帮我看看完整的推荐方向列表，对比一下各个选项"},
                            {"label": "这个方向市场需求怎么样", "prompt": f"「{top_label}」的市场需求、薪资水平和发展前景怎么样？"},
                        ]

                    greeting = (
                        f"分析完了，{profile_name}！"
                        f"根据你的背景，我觉得「{top_label}」最适合你（匹配度 {top_pct}%）。\n\n"
                        f"{signal}"
                    )
                else:
                    # Fallback: no recommendation data
                    greeting = (
                        f"画像建好了，{profile_name}！我识别到你有 {skill_count} 项技能。\n\n"
                        f"你有感兴趣的方向吗？或者让我帮你分析最匹配的。"
                    )
                    chips = [
                        {"label": "帮我分析最匹配的方向", "prompt": "根据我的技能和项目背景，帮我分析最匹配的职业方向，解释为什么"},
                        {"label": "我对某个方向感兴趣", "prompt": "我对一个职业方向感兴趣，想了解更多"},
                        {"label": "我还不确定方向怎么办", "prompt": "我现在完全不知道该往哪个方向发展，帮我理清思路"},
                    ]

    elif stage == "has_profile" and goal:
        greeting = (
            f"{profile_name}，你已经把「{goal.target_label}」设为成长方向了。\n\n"
            f"下一步最有价值的事：找一份这个方向的真实 JD，粘贴过来做匹配度诊断——"
            f"看清楚你和岗位的真实差距，比猜测有用得多。"
        )
        chips = [
            {"label": "诊断一份JD", "prompt": "诊断 JD 匹配度"},
            {"label": f"成为{goal.target_label}核心要什么", "prompt": f"成为{goal.target_label}最核心的技能和经验是什么？"},
            {"label": "我现在差距有多大", "prompt": f"基于我的画像，我距离{goal.target_label}的差距主要在哪几块？"},
        ]

    elif stage == "first_diagnosis":
        score_part = f"匹配度 {latest_jd_score}%，" if latest_jd_score else ""
        gap_part = f"发现 {gap_count} 个技能缺口" if gap_count else "发现了一些技能缺口"
        greeting = (
            f"上次 JD 诊断{score_part}{gap_part}。\n\n"
            f"一份 JD 的数据太少，多诊断几份才能看清市场的真实要求——不同公司、不同规模的 JD 差异很大。"
        )
        chips = [
            {"label": "再诊断一份JD", "prompt": "诊断 JD 匹配度"},
            {"label": "我的缺口怎么补", "prompt": "帮我看看目前最大的技能缺口，以及补齐的思路"},
            {"label": "找找更多同类岗位JD", "prompt": "帮我搜索一些我目标方向的招聘信息，看看市场要求"},
        ]

    elif stage == "training":
        greeting = (
            f"你已经诊断了 {jd_count} 份 JD，对市场要求有了初步感知。\n\n"
            f"下一步可以做技能校准——用一两道面试题测测自己的真实水平，"
            f"或者继续扩大 JD 样本，看看不同公司的差异。"
        )
        chips = [
            {"label": "出一道题校准一下", "prompt": "出一道面试题校准一下，不用太难，帮我了解自己的真实水平"},
            {"label": "再诊断一份JD", "prompt": "诊断 JD 匹配度"},
            {"label": "看看成长数据", "prompt": "查看我的成长数据和进度"},
        ]

    elif stage == "growing":
        greeting = (
            f"你已经积累了 {jd_count} 次诊断，数据很扎实了！\n\n"
            f"现在可以生成一份职业发展报告，把你的能力画像、市场差距和成长轨迹系统梳理一下。"
        )
        chips = [
            {"label": "生成职业报告", "prompt": "帮我生成职业分析报告"},
            {"label": "看看成长看板", "prompt": "查看我的成长数据"},
            {"label": "再诊断一份JD", "prompt": "诊断 JD 匹配度"},
        ]

    else:  # report_ready
        lp = f"学习进度 {learning_pct}%，" if learning_pct > 0 else ""
        greeting = (
            f"你的职业规划闭环已经跑通了！{lp}继续保持。\n\n"
            f"可以做新的诊断、更新画像，或者聊聊下一阶段的发展方向。"
        )
        chips = [
            {"label": "做新的JD诊断", "prompt": "诊断 JD 匹配度"},
            {"label": "更新职业报告", "prompt": "帮我生成职业分析报告"},
            {"label": "聊聊下一步", "prompt": "我接下来应该重点提升什么能力？"},
        ]

    # Inject market card for target direction (if user has a goal)
    market_card = None
    if goal and goal.target_node_id:
        market_card = _get_card_for_node(goal.target_node_id)

    # processing=True signals frontend to auto-refresh greeting after a few seconds
    is_processing = (stage == "has_profile" and not goal and not recs_ready)

    return {
        "stage": stage,
        "greeting": greeting,
        "chips": chips,
        "market_card": market_card,
        "processing": is_processing,
        "context": {
            "profile_name": profile_name,
            "skill_count": skill_count,
            "goal_label": goal.target_label if goal else None,
            "jd_count": jd_count,
            "learning_pct": learning_pct,
        },
    }


@router.get("/greeting")
def chat_greeting(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return stage-aware greeting + dynamic chips for the chat panel."""
    return _build_greeting(user, db)


def _generate_session_title(session_id: int, user_id: int) -> None:
    """Background: generate LLM-based title after 2 rounds of conversation."""
    from backend.db import SessionLocal
    from backend.llm import get_model, llm_chat

    db = SessionLocal()
    try:
        session = db.query(ChatSession).filter_by(id=session_id).first()
        if not session:
            return

        msg_count = (
            db.query(func.count(ChatMessage.id))
            .filter(ChatMessage.session_id == session_id)
            .scalar() or 0
        )
        if msg_count < 4:  # Need at least 2 rounds (2 user + 2 assistant)
            return

        # Only generate if title is still the default truncation
        first_msg = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id, ChatMessage.role == "user")
            .order_by(ChatMessage.created_at)
            .first()
        )
        if not first_msg or session.title != first_msg.content[:50]:
            return  # Already has a generated title

        # Gather first few messages for context
        msgs = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .limit(6)
            .all()
        )
        conversation = "\n".join(f"{m.role}: {m.content[:100]}" for m in msgs)

        title = llm_chat(
            [
                {
                    "role": "system",
                    "content": (
                        "根据以下对话生成一个简短中文标题（不超过15个字）。"
                        "直接输出标题，不加引号、标点或解释。"
                    ),
                },
                {"role": "user", "content": conversation},
            ],
            model=get_model("fast"),
            temperature=0.3,
            timeout=10,
        )
        title = title.strip().strip("\"'「」''""")[:20]
        if not title:
            return

        # Deduplicate: check existing titles for this user
        existing = (
            db.query(ChatSession.title)
            .filter(
                ChatSession.user_id == user_id,
                ChatSession.id != session_id,
                ChatSession.title.like(f"{title}%"),
            )
            .all()
        )
        existing_titles = {t[0] for t in existing}
        if title in existing_titles:
            for i in range(2, 100):
                candidate = f"{title} ({i})"
                if candidate not in existing_titles:
                    title = candidate
                    break

        session.title = title
        db.commit()
        logger.info("Generated session title: %s (session=%d)", title, session_id)
    except Exception:
        logger.exception("Failed to generate session title")
    finally:
        db.close()


def _update_coach_memo(session_id: int, user_id: int) -> None:
    """Background: 把本次对话喂给 Mem0，让它自动抽取记忆。

    Mem0 内置 LLM extraction + 去重 + 冲突合并，我们只负责喂对话。
    老的 profile.coach_memo 文本在首次调用时一次性迁移进 Mem0。
    """
    from backend.db import SessionLocal
    from backend.db_models import ChatMessage, Profile
    from backend.services.coach_memory import add_conversation, migrate_legacy_memo
    from sqlalchemy import func

    db = SessionLocal()
    try:
        msg_count = (
            db.query(func.count(ChatMessage.id))
            .filter(ChatMessage.session_id == session_id)
            .scalar() or 0
        )
        if msg_count < 6:
            return

        profile = (
            db.query(Profile)
            .filter_by(user_id=user_id)
            .order_by(Profile.updated_at.desc())
            .first()
        )

        # 迁移老 memo（幂等，Mem0 自动去重）
        if profile and profile.coach_memo:
            migrate_legacy_memo(user_id, profile.coach_memo)
            profile.coach_memo = ""  # 迁移后清空，避免重复
            db.commit()

        # 喂本次对话给 Mem0
        msgs = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .limit(20)
            .all()
        )
        conversation = "\n".join(f"{m.role}: {m.content[:300]}" for m in msgs)
        add_conversation(user_id, conversation)
        logger.info("Coach memory updated via Mem0 for user %d", user_id)
    except Exception:
        logger.exception("Failed to update coach memory")
    finally:
        db.close()


async def _build_event_stream(req: ChatRequest, user: User, db: Session):
    """Core SSE generator — plain `data:` lines, no named events."""
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage as LCToolMessage, SystemMessage as LCSystemMessage

    # ── Step 1: Create/load session FIRST, send session_id immediately ──
    try:
        if req.session_id:
            session = (
                db.query(ChatSession)
                .filter(
                    ChatSession.id == req.session_id,
                    ChatSession.user_id == user.id,
                )
                .first()
            )
        else:
            session = ChatSession(user_id=user.id, title=req.message[:50])
            db.add(session)
            db.flush()

        if session:
            # Save user message immediately
            db.add(
                ChatMessage(
                    session_id=session.id,
                    role="user",
                    content=req.message,
                )
            )
            db.commit()
            # Send session_id to frontend right away
            yield f"data: {json.dumps({'session_id': session.id})}\n\n"
    except Exception:
        logger.exception("Failed to create chat session")
        session = None

    # ── Step 2: Load conversation history + stream LLM response ──
    supervisor = _get_supervisor()
    initial_state = _hydrate_state(user, db)

    messages = []

    # Load prior messages from DB for cross-turn memory
    if session:
        prior_msgs = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at)
            .limit(40)
            .all()
        )
        for m in prior_msgs:
            if m.role == "user":
                messages.append(HumanMessage(content=m.content))
            else:
                messages.append(AIMessage(content=m.content))
    else:
        # Fallback to request history if no session
        for h in (req.history or []):
            if h.get("role") == "user":
                messages.append(HumanMessage(content=h["content"]))
            else:
                messages.append(AIMessage(content=h["content"]))
        messages.append(HumanMessage(content=req.message))

    initial_state["messages"] = messages
    if req.page_context:
        initial_state["page_context"] = {
            "route": req.page_context.route,
            "label": req.page_context.label,
            "data": req.page_context.data,
        }

    full_response = ""
    agent_source = "coach_agent"  # Track which node produced the response
    agent_source_sent = False  # Whether we've sent the agent_source SSE event
    tool_messages: list = []  # Collect tool messages for structured data extraction

    # TTFT instrumentation (2026-04-15)
    import time as _time
    _ttft_start = _time.time()
    _first_chunk_logged = False

    # Pre-scan user message for direction mentions (user-side trigger)
    user_detected_cards = _extract_market_cards(req.message)

    # Also inject from page context if user is on a role detail page
    if req.page_context and req.page_context.route.startswith("/roles/"):
        page_node_id = req.page_context.route.split("/roles/")[-1].split("/")[0].strip()
        if page_node_id:
            page_card = _get_card_for_node(page_node_id)
            if page_card:
                existing_families = {c["family"] for c in user_detected_cards}
                if page_card["family"] not in existing_families:
                    user_detected_cards = [page_card] + user_detected_cards

    # Trailing buffer: keep last 24 chars un-emitted so [COACH_RESULT_ID:NNNNN]
    # markers (23 chars max) don't flash before we strip them at stream end.
    _TAIL = 24
    _stream_tail = ""
    import re as _re

    try:
        async for msg_chunk, metadata in supervisor.astream(
            initial_state,
            stream_mode="messages",
        ):
            node_name = metadata.get("langgraph_node", "")

            # ── Tool messages arrive complete (not chunked) ─────────────────
            if isinstance(msg_chunk, LCToolMessage):
                tool_messages.append(msg_chunk)
                _tm_content = getattr(msg_chunk, "content", "")
                if "[JD_SEARCH_RESULTS:" in _tm_content:
                    _jd_match = _re.search(r'\[JD_SEARCH_RESULTS:(.*)\]', _tm_content, _re.DOTALL)
                    if _jd_match:
                        try:
                            _jd_data = json.loads(_jd_match.group(1))
                            yield f"data: {json.dumps({'jd_cards': _jd_data}, ensure_ascii=False)}\n\n"
                        except (json.JSONDecodeError, Exception):
                            logger.warning("Failed to parse JD search results from tool message")
                continue

            if isinstance(msg_chunk, (LCSystemMessage, HumanMessage)):
                continue

            # Skip tool-call request chunks (contain tool_calls, no text)
            if getattr(msg_chunk, "tool_calls", None):
                continue

            _chunk_content = getattr(msg_chunk, "content", "")
            if not _chunk_content:
                continue

            # ── Track which agent is responding ─────────────────────────────
            if node_name not in ("triage", "handoff_executor", "__start__", "__end__"):
                agent_source = node_name
                if not agent_source_sent:
                    agent_source_sent = True
                    yield f"data: {json.dumps({'agent': agent_source}, ensure_ascii=False)}\n\n"

            full_response += _chunk_content
            _stream_tail += _chunk_content

            # Flush safe prefix (all but last _TAIL chars) to avoid emitting partial markers
            if len(_stream_tail) > _TAIL:
                _safe = _stream_tail[:-_TAIL]
                _safe = _re.sub(r'\[COACH_RESULT_ID:\d+\]', '', _safe)
                if _safe:
                    if not _first_chunk_logged:
                        logger.info("TTFT: %.0f ms user=%d", (_time.time()-_ttft_start)*1000, user.id)
                        _first_chunk_logged = True
                    yield f"data: {json.dumps({'content': _safe}, ensure_ascii=False)}\n\n"
                _stream_tail = _stream_tail[-_TAIL:]

    except Exception as e:
        logger.exception("Chat stream error")
        yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    # ── Flush tail buffer (strip markers) ───────────────────────────────────
    if _stream_tail:
        _tail_clean = _re.sub(r'\[COACH_RESULT_ID:\d+\]', '', _stream_tail)
        # Also strip JD_SEARCH_RESULTS if LLM embedded it in text (post-stream safe)
        _tail_clean = _re.sub(r'\[JD_SEARCH_RESULTS:.*?\]', '', _tail_clean, flags=_re.DOTALL)
        if _tail_clean.strip():
            yield f"data: {json.dumps({'content': _tail_clean}, ensure_ascii=False)}\n\n"

    # Post-stream: handle JD_SEARCH_RESULTS embedded in full AI response text
    _jd_in_ai = _re.search(r'\[JD_SEARCH_RESULTS:(.*)\]', full_response, _re.DOTALL)
    if _jd_in_ai and not any(
        "[JD_SEARCH_RESULTS:" in getattr(tm, "content", "") for tm in tool_messages
    ):
        try:
            _jd_data_ai = json.loads(_jd_in_ai.group(1))
            yield f"data: {json.dumps({'jd_cards': _jd_data_ai}, ensure_ascii=False)}\n\n"
        except (json.JSONDecodeError, Exception):
            pass

    # ── Step 2.5: Emit market_cards based on user's career goal (deterministic) ──
    # Previously: parsed AI free text with keyword aliases → unreliable, context-blind
    # Now: use career_goal.target_node_id → always accurate, no text parsing
    _DIRECTION_AGENTS = {"coach_agent", "navigator", "profile_agent", "growth_agent"}
    if agent_source in _DIRECTION_AGENTS:
        goal_info = initial_state.get("career_goal")
        goal_node_id = goal_info.get("node_id") if goal_info else None
        if goal_node_id:
            goal_card = _get_card_for_node(goal_node_id)
            if goal_card:
                yield f"data: {json.dumps({'market_cards': [goal_card]}, ensure_ascii=False)}\n\n"

    # ── Step 3: Save response + optionally create CoachResult card ──
    if session and full_response:
        try:
            db.add(
                ChatMessage(
                    session_id=session.id,
                    role="assistant",
                    content=full_response,
                )
            )
            db.commit()
            # Trigger background title generation + memo update (fire-and-forget)
            threading.Thread(
                target=_generate_session_title,
                args=(session.id, user.id),
                daemon=True,
            ).start()
            threading.Thread(
                target=_update_coach_memo,
                args=(session.id, user.id),
                daemon=True,
            ).start()
        except Exception:
            logger.exception("Failed to save assistant message")

    # Check if any tool already saved a CoachResult
    # Strategy (most reliable → least):
    #   1. Marker in tool messages (tool returned [COACH_RESULT_ID:N])
    #   2. Marker in LLM response (LLM echoed it)
    #   3. DB fallback: query recent CoachResult for this user (LLM forgot the marker)
    import re
    from datetime import timedelta
    coach_result_id = None

    # Check tool messages first
    for tm in tool_messages:
        content = getattr(tm, "content", "")
        if isinstance(content, list):
            # Some LangChain versions return content as list of dicts
            content = " ".join(
                c.get("text", "") if isinstance(c, dict) else str(c) for c in content
            )
        m = re.search(r'\[COACH_RESULT_ID:(\d+)\]', str(content))
        if m:
            coach_result_id = int(m.group(1))
            break

    # Also check the full response (agent may echo the marker)
    if not coach_result_id:
        m = re.search(r'\[COACH_RESULT_ID:(\d+)\]', full_response)
        if m:
            coach_result_id = int(m.group(1))
            full_response = re.sub(r'\[COACH_RESULT_ID:\d+\]', '', full_response).strip()

    # DB fallback: unconditional — query for any recent CoachResult created by a tool
    # during this request. This handles:
    #  - LLM ignoring [COACH_RESULT_ID:N] marker
    #  - agent_source not being set to "jd_agent" (nested graph node naming issues)
    #  - ToolMessage content format differences (list vs str) across LangChain versions
    if not coach_result_id:
        try:
            from datetime import datetime, timezone
            cutoff = datetime.now(timezone.utc) - timedelta(seconds=60)
            recent_cr = (
                db.query(CoachResult)
                .filter(
                    CoachResult.user_id == user.id,
                    CoachResult.created_at >= cutoff,
                )
                .order_by(CoachResult.created_at.desc())
                .first()
            )
            if recent_cr:
                coach_result_id = recent_cr.id
                logger.info(
                    "DB fallback: found %s CoachResult id=%d for user %d (agent_source=%s)",
                    recent_cr.result_type, recent_cr.id, user.id, agent_source,
                )
        except Exception:
            logger.exception("DB fallback for CoachResult failed")

    if coach_result_id:
        # Tool already saved the CoachResult — fix user_id/session_id and emit the card
        try:
            cr = db.query(CoachResult).filter_by(id=coach_result_id).first()
            # Always bind session_id + ensure correct user_id
            if cr:
                needs_commit = False
                if cr.user_id != user.id:
                    cr.user_id = user.id
                    needs_commit = True
                if session and cr.session_id != session.id:
                    cr.session_id = session.id
                    needs_commit = True
                if needs_commit:
                    db.commit()
            if cr:
                meta = json.loads(cr.metadata_json or "{}")
                card_payload: dict = {
                    "type": cr.result_type,
                    "id": cr.id,
                    "title": cr.title,
                    "score": meta.get("match_score"),
                    "gap_count": meta.get("gap_count"),
                }
                # For jd_diagnosis, also carry jd_title + company + job_url for "加入实战追踪"
                if cr.result_type == "jd_diagnosis":
                    try:
                        detail = json.loads(cr.detail_json or "{}")
                        card_payload["jd_title"] = detail.get("jd_title", "")
                        card_payload["company"] = detail.get("company", "")
                        card_payload["job_url"] = detail.get("job_url", "")
                    except Exception:
                        pass
                card_data = {"card": card_payload}
                yield f"data: {json.dumps(card_data, ensure_ascii=False)}\n\n"
        except Exception:
            logger.exception("Failed to emit CoachResult card")
    elif full_response and agent_source in ("growth_agent", "navigator", "profile_agent") and len(full_response) > 300:
        # Auto-save CoachResult for agents with substantial responses
        try:
            result_type_map = {
                "jd_agent": "jd_diagnosis",
                "growth_agent": "growth_analysis",
                "navigator": "career_exploration",
                "profile_agent": "profile_analysis",
            }
            result_type = result_type_map.get(agent_source, "general")
            title = f"{req.message[:40]}..."
            summary_text = full_response.split("\n\n")[0][:200] if "\n\n" in full_response else full_response[:200]

            coach_result = CoachResult(
                user_id=user.id,
                session_id=session.id if session else None,
                result_type=result_type,
                title=title,
                summary=summary_text,
                detail_json=json.dumps({"raw_text": full_response}, ensure_ascii=False),
                metadata_json=json.dumps({"agent": agent_source}, ensure_ascii=False),
            )
            db.add(coach_result)
            db.commit()

            card_data = {
                "card": {
                    "type": result_type,
                    "id": coach_result.id,
                    "title": title,
                }
            }
            yield f"data: {json.dumps(card_data, ensure_ascii=False)}\n\n"
        except Exception:
            logger.exception("Failed to save CoachResult")

    yield "data: [DONE]\n\n"


@router.post("")
@router.post("/")
async def chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """SSE streaming chat — frontend primary endpoint (POST /api/chat)."""
    import asyncio

    _SSE_TIMEOUT = 120  # 2 minutes max per chat turn

    async def _guarded_stream():
        """Wrap the event stream with an overall timeout."""
        try:
            async with asyncio.timeout(_SSE_TIMEOUT):
                async for chunk in _build_event_stream(req, user, db):
                    yield chunk
        except TimeoutError:
            logger.warning("SSE stream timed out after %ds for user %s", _SSE_TIMEOUT, user.id)
            yield 'data: {"error": "响应超时，请重试"}\n\n'
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.exception("SSE stream error for user %s: %s", user.id, e)
            yield 'data: {"error": "服务异常，请稍后重试"}\n\n'
            yield "data: [DONE]\n\n"

    return StreamingResponse(_guarded_stream(), media_type="text/event-stream")


# ── FR37: Chat session CRUD ──────────────────────────────────────────────────

@router.get("/sessions")
def list_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List chat sessions for the current user."""
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return [
        {
            "id": s.id,
            "title": s.title,
            "updated_at": str(s.updated_at),
        }
        for s in sessions
    ]


@router.get("/sessions/{session_id}/messages")
def get_messages(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all messages in a chat session."""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(404, "会话不存在")
    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return [
        {
            "role": m.role,
            "content": m.content,
            "created_at": str(m.created_at),
        }
        for m in msgs
    ]


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a chat session and its messages."""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(404, "会话不存在")
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"message": "已删除"}
