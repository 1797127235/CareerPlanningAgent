# -*- coding: utf-8 -*-
"""Browser extension router.

Endpoints:
  POST /api/extension/token          — generate / refresh token (user auth)
  GET  /api/extension/token          — get current token (user auth)
  POST /api/extension/jd             — receive JD from extension (token auth)
  GET  /api/extension/pending/{sid}  — frontend polls for pending JD (user auth)
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import backend.pending_jds as pending_jds
from backend.auth import get_current_user
from backend.db import get_db
from backend.db_models import ExtensionToken, User

router = APIRouter()

_TOKEN_TTL_DAYS = 365


# ── Token management ─────────────────────────────────────────────


@router.post("/token")
def generate_token(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate (or replace) the extension token for the current user."""
    db.query(ExtensionToken).filter(ExtensionToken.user_id == user.id).delete()
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=_TOKEN_TTL_DAYS)
    db.add(ExtensionToken(user_id=user.id, token=token, expires_at=expires_at))
    db.commit()
    return {"token": token, "expires_at": expires_at.isoformat()}


@router.get("/token")
def get_token(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the active token, or null if none exists."""
    row = (
        db.query(ExtensionToken)
        .filter(
            ExtensionToken.user_id == user.id,
            ExtensionToken.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )
    if not row:
        return {"token": None}
    return {"token": row.token, "expires_at": row.expires_at.isoformat()}


# ── Extension → backend ──────────────────────────────────────────


class ExtensionJDRequest(BaseModel):
    jd_text: str
    page_title: str = ""
    source_url: str = ""


@router.post("/jd")
def receive_jd(
    req: ExtensionJDRequest,
    x_extension_token: str = Header(...),
    db: Session = Depends(get_db),
):
    """Accept a JD payload from the browser extension."""
    row = (
        db.query(ExtensionToken)
        .filter(
            ExtensionToken.token == x_extension_token,
            ExtensionToken.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )
    if not row:
        raise HTTPException(401, "令牌无效或已过期，请在扩展设置中重新生成")

    session_id = pending_jds.put(req.jd_text, req.source_url)
    return {"session_id": session_id}


# ── Frontend polling ─────────────────────────────────────────────


@router.get("/pending/{session_id}")
def get_pending_jd(
    session_id: str,
    _user: User = Depends(get_current_user),
):
    """Consume a pending JD by session_id (one-shot)."""
    entry = pending_jds.pop(session_id)
    if not entry:
        raise HTTPException(404, "会话不存在或已过期")
    return entry
