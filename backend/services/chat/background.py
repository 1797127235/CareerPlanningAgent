"""Background tasks for chat sessions: title generation + coach memory."""
from __future__ import annotations

import logging

from sqlalchemy import func

from backend.db import SessionLocal
from backend.models import ChatMessage, ChatSession, Profile
from backend.services.coach.memory import add_conversation, migrate_legacy_memo
from backend.llm import get_model, llm_chat

logger = logging.getLogger(__name__)


def generate_session_title(session_id: int, user_id: int) -> None:
    """Background: generate LLM-based title after 2 rounds of conversation."""
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
        title = title.strip().strip("\"'「」''\"")[:20]
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


def update_coach_memo(session_id: int, user_id: int) -> None:
    """Background: feed conversation into Mem0 for memory extraction.

    Mem0 handles LLM extraction + dedup + conflict merging internally.
    Legacy profile.coach_memo is migrated into Mem0 on first call.
    """
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

        # Migrate old memo (idempotent, Mem0 auto-dedup)
        if profile and profile.coach_memo:
            migrate_legacy_memo(user_id, profile.coach_memo)
            profile.coach_memo = ""
            db.commit()

        # Feed conversation to Mem0
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
