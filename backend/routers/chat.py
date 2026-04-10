"""SSE chat endpoint — streams Supervisor multi-agent responses + session persistence."""
from __future__ import annotations

import json
import logging
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
    InterviewReview,
    JDDiagnosis,
    JobApplication,
    LearningProgress,
    Profile,
    ProjectRecord,
    Report,
    User,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_supervisor = None


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

    # 2. Career goal
    goal = (
        db.query(CareerGoal)
        .filter_by(user_id=user.id, is_active=True)
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
    review_count = (
        db.query(func.count(InterviewReview.id))
        .join(Profile, InterviewReview.profile_id == Profile.id)
        .filter(Profile.user_id == user.id)
        .scalar() or 0
    )
    report_count = db.query(func.count(Report.id)).filter_by(user_id=user.id).scalar() or 0

    state["user_stage"] = compute_stage(profile_count, jd_count, review_count, report_count)

    # 5. Growth coach state
    state["coach_memo"] = ""
    state["page_context"] = None
    state["tool_hint"] = ""
    state["last_active_agent"] = ""
    if profile:
        state["coach_memo"] = profile.coach_memo or ""

    # 6. Growth log context — projects + active pursuits
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

    return state


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
        .filter_by(user_id=user.id, is_active=True)
        .order_by(CareerGoal.set_at.desc())
        .first()
    )

    profile_count = db.query(func.count(Profile.id)).filter_by(user_id=user.id).scalar() or 0
    jd_count = db.query(func.count(JDDiagnosis.id)).filter_by(user_id=user.id).scalar() or 0
    review_count = (
        db.query(func.count(InterviewReview.id))
        .join(Profile, InterviewReview.profile_id == Profile.id)
        .filter(Profile.user_id == user.id)
        .scalar() or 0
    )
    report_count = db.query(func.count(Report.id)).filter_by(user_id=user.id).scalar() or 0

    stage = compute_stage(profile_count, jd_count, review_count, report_count)

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

    # Learning progress
    learning_pct = 0
    if profile and goal:
        total = (
            db.query(func.count(LearningProgress.id))
            .filter(
                LearningProgress.profile_id == profile.id,
                LearningProgress.node_id == goal.target_node_id,
            )
            .scalar() or 0
        )
        completed = (
            db.query(func.count(LearningProgress.id))
            .filter(
                LearningProgress.profile_id == profile.id,
                LearningProgress.node_id == goal.target_node_id,
                LearningProgress.completed == True,
            )
            .scalar() or 0
        )
        if total > 0:
            learning_pct = round(completed / total * 100)

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
        greeting = (
            f"{profile_name}，你的能力画像已经建好了，识别到 {skill_count} 项技能。\n\n"
            f"下一步：看看哪些岗位方向和你最匹配？去画像页查看系统推荐，或者告诉我你感兴趣的方向。"
        )
        chips = [
            {"label": "推荐适合我的方向", "prompt": "根据我的技能背景，推荐最适合我的岗位方向"},
            {"label": "诊断一份JD", "prompt": "诊断 JD 匹配度"},
            {"label": "我的技能有竞争力吗", "prompt": "分析一下我目前的技能在市场上的竞争力"},
        ]

    elif stage == "has_profile" and goal:
        greeting = (
            f"{profile_name}，你已经选了「{goal.target_label}」作为成长目标。\n\n"
            f"接下来建议找一份目标岗位的真实 JD，做匹配度诊断——看看差距在哪，才好制定计划。"
        )
        chips = [
            {"label": "诊断JD匹配度", "prompt": "诊断 JD 匹配度"},
            {"label": f"成为{goal.target_label}要什么技能", "prompt": f"成为{goal.target_label}需要哪些核心技能？"},
            {"label": "这个方向会被AI替代吗", "prompt": f"{goal.target_label}这个方向未来会被AI替代吗？"},
        ]

    elif stage == "first_diagnosis":
        score_part = f"匹配度 {latest_jd_score}%，" if latest_jd_score else ""
        gap_part = f"发现 {gap_count} 个技能缺口" if gap_count else "发现了一些技能缺口"
        greeting = (
            f"上次 JD 诊断{score_part}{gap_part}。\n\n"
            f"现在有两个选择：练面试题提升薄弱项，或者继续诊断更多 JD 看看市场需求。你想先做哪个？"
        )
        chips = [
            {"label": "练一道面试题", "prompt": "开始面试练习"},
            {"label": "再诊断一份JD", "prompt": "诊断 JD 匹配度"},
            {"label": "查看技能缺口", "prompt": "帮我看看目前最大的技能缺口是什么"},
        ]

    elif stage == "training":
        greeting = (
            f"你已经做了 {review_count} 次面试练习，正在积累实战经验。\n\n"
            f"建议继续练习，尤其是薄弱维度。数据积累到一定量后，可以生成职业发展报告。"
        )
        chips = [
            {"label": "继续练习面试", "prompt": "开始面试练习"},
            {"label": "看看成长数据", "prompt": "查看我的成长数据和进步曲线"},
            {"label": "哪个维度最弱", "prompt": "分析一下我面试练习中最薄弱的维度是什么"},
        ]

    elif stage == "growing":
        greeting = (
            f"你已经积累了 {jd_count} 次诊断、{review_count} 次面试练习，数据很丰富了！\n\n"
            f"现在可以生成一份完整的职业发展报告，梳理你的成长轨迹和下一步方向。"
        )
        chips = [
            {"label": "生成职业报告", "prompt": "帮我生成职业分析报告"},
            {"label": "看看成长看板", "prompt": "查看我的成长数据"},
            {"label": "做新的JD诊断", "prompt": "诊断 JD 匹配度"},
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

    return {
        "stage": stage,
        "greeting": greeting,
        "chips": chips,
        "context": {
            "profile_name": profile_name,
            "skill_count": skill_count,
            "goal_label": goal.target_label if goal else None,
            "jd_count": jd_count,
            "review_count": review_count,
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
    """Background: extract key insights from conversation and update coach_memo."""
    from backend.db import SessionLocal
    from backend.llm import get_model, llm_chat

    db = SessionLocal()
    try:
        # Need at least 3 rounds (6 messages) for meaningful memo
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
        if not profile:
            return

        # Get recent messages from this session
        msgs = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .limit(20)
            .all()
        )
        conversation = "\n".join(f"{m.role}: {m.content[:200]}" for m in msgs)
        current_memo = profile.coach_memo or ""

        updated = llm_chat(
            [
                {
                    "role": "system",
                    "content": (
                        "你是职业教练的记忆助手。根据本次对话更新用户备忘录。\n"
                        "规则：\n"
                        "- 保留仍相关的旧内容，融入新发现\n"
                        "- 记录：用户偏好、决策、关注点、目标变化、情绪状态\n"
                        "- 不记录：具体问题原文、JD内容、技术细节\n"
                        "- 总长度不超过500字\n"
                        "- 直接输出更新后的备忘录，不加解释"
                    ),
                },
                {
                    "role": "user",
                    "content": f"现有备忘录：\n{current_memo or '（空）'}\n\n本次对话：\n{conversation}",
                },
            ],
            model=get_model("fast"),
            temperature=0.3,
            timeout=15,
        )
        updated = updated.strip()[:600]
        if updated and updated != current_memo:
            profile.coach_memo = updated
            db.commit()
            logger.info("Updated coach_memo for user %d (len=%d)", user_id, len(updated))
    except Exception:
        logger.exception("Failed to update coach memo")
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

    try:
        async for event in supervisor.astream(
            initial_state,
            stream_mode="updates",
        ):
            for node_name, update in event.items():
                if "messages" not in update:
                    continue
                for msg in update["messages"]:
                    # Collect tool messages for structured data extraction
                    if isinstance(msg, LCToolMessage):
                        tool_messages.append(msg)
                        # Check for JD search results in tool output → emit immediately
                        _tm_content = getattr(msg, "content", "")
                        if "[JD_SEARCH_RESULTS:" in _tm_content:
                            import re as _re2
                            _jd_match = _re2.search(r'\[JD_SEARCH_RESULTS:(.*)\]', _tm_content, _re2.DOTALL)
                            if _jd_match:
                                try:
                                    _jd_data = json.loads(_jd_match.group(1))
                                    yield f"data: {json.dumps({'jd_cards': _jd_data}, ensure_ascii=False)}\n\n"
                                except (json.JSONDecodeError, Exception):
                                    logger.warning("Failed to parse JD search results from tool message")
                        continue
                    if isinstance(msg, LCSystemMessage):
                        continue
                    # Skip user messages — only stream AI responses
                    if isinstance(msg, HumanMessage):
                        continue
                    if (
                        hasattr(msg, "content")
                        and msg.content
                        and not getattr(msg, "tool_calls", None)
                    ):
                        # Track which agent produced this and notify frontend
                        if node_name not in ("triage", "handoff_executor", "__start__", "__end__"):
                            agent_source = node_name
                            if not agent_source_sent:
                                agent_source_sent = True
                                yield f"data: {json.dumps({'agent': agent_source}, ensure_ascii=False)}\n\n"
                        # Strip internal markers before streaming to frontend
                        import re as _re
                        content_to_stream = msg.content

                        # Extract JD search results marker → emit as separate SSE event
                        jd_search_match = _re.search(
                            r'\[JD_SEARCH_RESULTS:(.*)\]', content_to_stream, _re.DOTALL
                        )
                        if jd_search_match:
                            try:
                                jd_cards_json = jd_search_match.group(1)
                                jd_cards_data = json.loads(jd_cards_json)
                                yield f"data: {json.dumps({'jd_cards': jd_cards_data}, ensure_ascii=False)}\n\n"
                            except (json.JSONDecodeError, Exception):
                                logger.warning("Failed to parse JD search results JSON")
                            content_to_stream = _re.sub(
                                r'\[JD_SEARCH_RESULTS:.*\]', '', content_to_stream, flags=_re.DOTALL
                            )

                        clean_content = _re.sub(r'\[COACH_RESULT_ID:\d+\]', '', content_to_stream)
                        if clean_content.strip():
                            full_response += msg.content
                            yield (
                                f"data: {json.dumps({'content': clean_content}, ensure_ascii=False)}\n\n"
                            )

    except Exception as e:
        logger.exception("Chat stream error")
        yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

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
    # The marker [COACH_RESULT_ID:N] can appear in tool messages OR in the agent's final response
    import re
    coach_result_id = None

    # Check tool messages first
    for tm in tool_messages:
        content = getattr(tm, "content", "")
        m = re.search(r'\[COACH_RESULT_ID:(\d+)\]', content)
        if m:
            coach_result_id = int(m.group(1))
            break

    # Also check the full response (agent may echo the marker)
    if not coach_result_id:
        m = re.search(r'\[COACH_RESULT_ID:(\d+)\]', full_response)
        if m:
            coach_result_id = int(m.group(1))
            # Strip the marker from the saved response
            full_response = re.sub(r'\[COACH_RESULT_ID:\d+\]', '', full_response).strip()

    if coach_result_id:
        # Tool already saved the CoachResult — fix user_id and emit the card
        try:
            cr = db.query(CoachResult).filter_by(id=coach_result_id).first()
            # Ensure the CoachResult belongs to the current user
            if cr and cr.user_id != user.id:
                cr.user_id = user.id
                if session:
                    cr.session_id = session.id
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
                # For jd_diagnosis, also carry jd_title for "加入实战追踪"
                if cr.result_type == "jd_diagnosis":
                    try:
                        detail = json.loads(cr.detail_json or "{}")
                        card_payload["jd_title"] = detail.get("jd_title", "")
                    except Exception:
                        pass
                card_data = {"card": card_payload}
                yield f"data: {json.dumps(card_data, ensure_ascii=False)}\n\n"
        except Exception:
            logger.exception("Failed to emit CoachResult card")
    elif full_response and agent_source in ("report_agent",) and len(full_response) > 300:
        # Only auto-save CoachResult for report agent (JD uses structured save via tool)
        try:
            result_type_map = {
                "jd_agent": "jd_diagnosis",
                "report_agent": "career_report",
                "growth_agent": "growth_analysis",
                "practice_agent": "interview_review",
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
