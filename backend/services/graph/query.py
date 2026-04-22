"""Graph positioning, embedding pre-filter, LLM matching, and recommendations."""
from __future__ import annotations

import json
import logging
from pathlib import Path






logger = logging.getLogger(__name__)

_ROLE_LIST_CACHE: str | None = None    # invalidated when graph.json mtime changes
_GRAPH_NODES_CACHE: dict | None = None
_graph_mtime: float = 0.0             # tracks graph.json modification time

_GRAPH_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "graph.json"


def _graph_changed() -> bool:
    """Return True if graph.json was modified since last load."""
    global _graph_mtime
    try:
        mtime = _GRAPH_PATH.stat().st_mtime
    except OSError:
        return False
    if mtime != _graph_mtime:
        _graph_mtime = mtime
        return True
    return False


def _invalidate_graph_cache() -> None:
    """Clear all module-level graph caches (called when graph.json changes)."""
    global _GRAPH_NODES_CACHE, _ROLE_LIST_CACHE
    _GRAPH_NODES_CACHE = None
    _ROLE_LIST_CACHE = None
    logger.info("Graph caches invalidated due to graph.json update")


def _get_graph_nodes() -> dict:
    """Load graph.json nodes as dict keyed by node_id (cache invalidated on file change)."""
    global _GRAPH_NODES_CACHE
    if _graph_changed():
        _invalidate_graph_cache()
    if _GRAPH_NODES_CACHE is not None:
        return _GRAPH_NODES_CACHE
    with open(_GRAPH_PATH, "r", encoding="utf-8") as f:
        _GRAPH_NODES_CACHE = {n["node_id"]: n for n in json.load(f).get("nodes", [])}
    return _GRAPH_NODES_CACHE


def _get_role_list_text(node_ids: list[str] | None = None) -> str:
    """Build a role list string for the LLM prompt, including distinguishing_features."""
    global _ROLE_LIST_CACHE
    graph_nodes = _get_graph_nodes()

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
        return "\n".join(_format_node(nid, graph_nodes.get(nid, {})) for nid in node_ids)

    if _ROLE_LIST_CACHE:
        return _ROLE_LIST_CACHE
    _ROLE_LIST_CACHE = "\n".join(_format_node(nid, n) for nid, n in graph_nodes.items())
    return _ROLE_LIST_CACHE
