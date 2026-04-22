"""SSE chat endpoint — streams Supervisor multi-agent responses + session persistence."""
from __future__ import annotations

import asyncio
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
from backend.models import (
    ChatMessage,
    ChatSession,
    CoachResult,
    User,
)
from backend.services.chat import (
    build_greeting,
    extract_market_cards,
    generate_session_title,
    get_card_for_node,
    hydrate_state,
    update_coach_memo,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class PageContext(BaseModel):
    route: str = ""
    label: str = ""
    data: dict = {}


class ChatRequest(BaseModel):
    message: str
    session_id: int | None = None
    history: list[dict] = []
    page_context: PageContext | None = None


async def _build_event_stream(req: ChatRequest, user: User, db: Session):
    """Core SSE generator — plain `data:` lines, no named events."""
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage as LCToolMessage, SystemMessage as LCSystemMessage
    from agent.supervisor import stream_chat_response

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
    initial_state = hydrate_state(user, db)

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
    user_detected_cards = extract_market_cards(req.message)

    # Also inject from page context if user is on a role detail page
    if req.page_context and req.page_context.route.startswith("/roles/"):
        page_node_id = req.page_context.route.split("/roles/")[-1].split("/")[0].strip()
        if page_node_id:
            page_card = get_card_for_node(page_node_id)
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
        async for msg_chunk, metadata in stream_chat_response(initial_state):
            node_name = metadata.get("langgraph_node", "")
            is_native_stream = metadata.get("streaming", False)

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

            if is_native_stream:
                # Native streaming: yield immediately, no tail buffer needed
                _clean = _re.sub(r'\[COACH_RESULT_ID:\d+\]', '', _chunk_content)
                if _clean:
                    if not _first_chunk_logged:
                        logger.info("TTFT: %.0f ms user=%d", (_time.time()-_ttft_start)*1000, user.id)
                        _first_chunk_logged = True
                    logger.info("SSE yield chunk: len=%d content=%r", len(_clean), _clean[:30])
                    yield f"data: {json.dumps({'content': _clean}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0)
            else:
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
    _DIRECTION_AGENTS = {"coach_agent", "navigator", "profile_agent", "growth_agent"}
    if agent_source in _DIRECTION_AGENTS:
        goal_info = initial_state.get("career_goal")
        goal_node_id = goal_info.get("node_id") if goal_info else None
        if goal_node_id:
            goal_card = get_card_for_node(goal_node_id)
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
                target=generate_session_title,
                args=(session.id, user.id),
                daemon=True,
            ).start()
            threading.Thread(
                target=update_coach_memo,
                args=(session.id, user.id),
                daemon=True,
            ).start()
        except Exception:
            logger.exception("Failed to save assistant message")

    # Check if any tool already saved a CoachResult
    import re
    from datetime import timedelta
    coach_result_id = None

    # Check tool messages first
    for tm in tool_messages:
        content = getattr(tm, "content", "")
        if isinstance(content, list):
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


@router.get("/greeting")
def chat_greeting(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return stage-aware greeting + dynamic chips for the chat panel."""
    return build_greeting(user, db)


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

    return StreamingResponse(
        _guarded_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
