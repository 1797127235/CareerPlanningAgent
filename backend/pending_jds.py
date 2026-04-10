# -*- coding: utf-8 -*-
"""In-memory pending JD store with TTL eviction.

Usage:
    sid = put(jd_text, source_url)   # store, returns session_id
    entry = pop(sid)                  # consume once; returns None if missing/expired
"""
from __future__ import annotations

import time
import uuid

_TTL = 600  # seconds
_store: dict[str, dict] = {}


def put(jd_text: str, source_url: str) -> str:
    _evict()
    sid = str(uuid.uuid4())
    _store[sid] = {"jd_text": jd_text, "source_url": source_url, "ts": time.time()}
    return sid


def pop(sid: str) -> dict | None:
    entry = _store.pop(sid, None)
    if entry and time.time() - entry["ts"] < _TTL:
        return {"jd_text": entry["jd_text"], "source_url": entry["source_url"]}
    return None


def _evict() -> None:
    now = time.time()
    stale = [k for k, v in _store.items() if now - v["ts"] >= _TTL]
    for k in stale:
        del _store[k]
