"""Graph data cache — single source of truth for graph.json and market_signals.json.

All modules should import from here instead of reading data files directly.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path


logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"

# ── Graph cache ─────────────────────────────────────────────────────────────
_ROLE_LIST_CACHE: str | None = None
_GRAPH_NODES_CACHE: dict | None = None
_GRAPH_RAW_CACHE: dict | None = None
_graph_mtime: float = 0.0

_GRAPH_PATH = _DATA_DIR / "graph.json"

# ── Market signals cache ────────────────────────────────────────────────────
_MARKET_SIGNALS_CACHE: dict | None = None
_market_mtime: float = 0.0

_MARKET_PATH = _DATA_DIR / "market_signals.json"


def _file_changed(path: Path, cached_mtime: float) -> float:
    """Return new mtime if file changed, else 0.0."""
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return 0.0
    return mtime if mtime != cached_mtime else 0.0


# ── Graph ───────────────────────────────────────────────────────────────────


def _invalidate_graph_cache() -> None:
    global _GRAPH_NODES_CACHE, _GRAPH_RAW_CACHE, _ROLE_LIST_CACHE
    _GRAPH_NODES_CACHE = None
    _GRAPH_RAW_CACHE = None
    _ROLE_LIST_CACHE = None
    logger.info("Graph caches invalidated due to graph.json update")


def _ensure_graph_loaded() -> None:
    global _GRAPH_NODES_CACHE, _GRAPH_RAW_CACHE, _graph_mtime
    new_mtime = _file_changed(_GRAPH_PATH, _graph_mtime)
    if new_mtime:
        _graph_mtime = new_mtime
        _invalidate_graph_cache()
    if _GRAPH_RAW_CACHE is not None:
        return
    with open(_GRAPH_PATH, "r", encoding="utf-8") as f:
        _GRAPH_RAW_CACHE = json.load(f)
    _GRAPH_NODES_CACHE = {n["node_id"]: n for n in _GRAPH_RAW_CACHE.get("nodes", [])}


def get_graph_nodes() -> dict:
    """Graph nodes dict keyed by node_id (cache invalidated on file change)."""
    _ensure_graph_loaded()
    return _GRAPH_NODES_CACHE


def get_graph_raw() -> dict:
    """Full parsed graph.json dict (nodes + edges)."""
    _ensure_graph_loaded()
    return _GRAPH_RAW_CACHE


def get_graph_edges() -> list[dict]:
    """Edges list from graph.json."""
    return get_graph_raw().get("edges", [])


# Private alias for backward compat
_get_graph_nodes = get_graph_nodes


# ── Market signals ──────────────────────────────────────────────────────────


def _invalidate_market_cache() -> None:
    global _MARKET_SIGNALS_CACHE
    _MARKET_SIGNALS_CACHE = None
    logger.info("Market signals cache invalidated")


def get_market_signals() -> dict:
    """Market signals dict (cache invalidated on file change)."""
    global _MARKET_SIGNALS_CACHE, _market_mtime
    new_mtime = _file_changed(_MARKET_PATH, _market_mtime)
    if new_mtime:
        _market_mtime = new_mtime
        _invalidate_market_cache()
    if _MARKET_SIGNALS_CACHE is not None:
        return _MARKET_SIGNALS_CACHE
    try:
        _MARKET_SIGNALS_CACHE = json.loads(_MARKET_PATH.read_text(encoding="utf-8"))
    except Exception:
        _MARKET_SIGNALS_CACHE = {}
    return _MARKET_SIGNALS_CACHE


# ── Role list text (for LLM prompts) ───────────────────────────────────────


def _get_role_list_text(node_ids: list[str] | None = None) -> str:
    """Build a role list string for the LLM prompt, including distinguishing_features."""
    global _ROLE_LIST_CACHE
    graph_nodes = get_graph_nodes()

    def _format_node(nid: str, n: dict) -> str:
        label = n.get("label", nid)
        cl = n.get("career_level", 0)
        ms = ", ".join(str(s) for s in (n.get("must_skills") or [])[:6])
        line = f"- {nid}: {label}（L{cl}，核心技能: {ms}）"
        df = n.get("distinguishing_features") or []
        if df:
            line += f"\n  适合信号: {'; '.join(df[:3])}"
        ntrf = n.get("not_this_role_if") or []
        if ntrf:
            line += f"\n  不适合: {'; '.join(ntrf[:2])}"
        return line

    if node_ids is not None:
        return "\n".join(
            _format_node(nid, graph_nodes.get(nid, {})) for nid in node_ids
        )

    if _ROLE_LIST_CACHE:
        return _ROLE_LIST_CACHE
    _ROLE_LIST_CACHE = "\n".join(_format_node(nid, n) for nid, n in graph_nodes.items())
    return _ROLE_LIST_CACHE
