# -*- coding: utf-8 -*-
"""Static data loaders and global state encapsulation for report service."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"

# ── Static data (loaded once per process) ─────────────────────────────────────

_GRAPH_NODES: dict[str, dict] = {}
_LEVEL_SKILLS: dict[str, dict] = {}
_MARKET: dict[str, dict] = {}        # family_name → signal dict
_NODE_TO_FAMILY: dict[str, str] = {} # node_id → family_name

_SKILL_FILL_PATH_PATH = _PROJECT_ROOT / "data" / "skill_fill_path_tags.json"
_SKILL_FILL_PATH_CACHE: dict[str, str] | None = None

# Career-alignment graph cache (auto-invalidates on mtime change)
_graph_cache: list[dict] | None = None
_graph_mtime: float = 0.0


_LEARN_KEYWORDS = {
    "数据结构", "算法", "操作系统", "计算机网络", "计算机组成",
    "数据库原理", "编译原理", "离散数学", "概率", "线性代数",
    "设计模式", "计算机体系", "机器学习原理",
}
_PRACTICE_KEYWORDS = {
    "高并发", "分布式", "性能优化", "架构", "微服务",
    "消息队列", "中间件", "负载均衡", "系统设计",
    "容灾", "秒杀", "限流",
}
_BOTH_KEYWORDS = {
    "Docker", "Kubernetes", "K8s", "Git", "CI/CD",
    "单元测试", "集成测试", "Code Review", "Terraform",
    "Prometheus", "Grafana",
}


def _load_skill_fill_path_cache() -> dict[str, str]:
    global _SKILL_FILL_PATH_CACHE
    if _SKILL_FILL_PATH_CACHE is not None:
        return _SKILL_FILL_PATH_CACHE
    if not _SKILL_FILL_PATH_PATH.exists():
        _SKILL_FILL_PATH_CACHE = {}
        return _SKILL_FILL_PATH_CACHE
    try:
        data = json.loads(_SKILL_FILL_PATH_PATH.read_text(encoding="utf-8"))
        _SKILL_FILL_PATH_CACHE = {k: v for k, v in data.items() if v in {"learn", "practice", "both"}}
    except Exception as e:
        logger.warning("Failed to load skill_fill_path_tags.json: %s", e)
        _SKILL_FILL_PATH_CACHE = {}
    return _SKILL_FILL_PATH_CACHE


def _classify_fill_path(skill_name: str, covered_by_project: bool = False) -> str:
    cache = _load_skill_fill_path_cache()
    if skill_name in cache:
        return cache[skill_name]
    s = skill_name.lower()
    for kw in _LEARN_KEYWORDS:
        if kw.lower() in s:
            return "learn"
    for kw in _PRACTICE_KEYWORDS:
        if kw.lower() in s:
            return "practice"
    for kw in _BOTH_KEYWORDS:
        if kw.lower() in s:
            return "both"
    return "practice" if covered_by_project else "both"


def _load_graph_nodes() -> list[dict]:
    """Load & cache graph.json nodes, auto-invalidate on mtime change."""
    global _graph_cache, _graph_mtime
    try:
        graph_path = _DATA_DIR / "graph.json"
        mtime = graph_path.stat().st_mtime
        if _graph_cache is None or mtime != _graph_mtime:
            with open(graph_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            _graph_cache = data.get("nodes", [])
            _graph_mtime = mtime
        return _graph_cache or []
    except Exception as e:
        logger.warning("Failed to load graph.json: %s", e)
        return []


def reload_static() -> None:
    """Force-reload all static data (call after regenerating data files)."""
    global _GRAPH_NODES, _LEVEL_SKILLS, _MARKET, _NODE_TO_FAMILY
    _GRAPH_NODES = {}
    _LEVEL_SKILLS = {}
    _MARKET = {}
    _NODE_TO_FAMILY = {}
    _load_static()


def _load_static() -> None:
    global _GRAPH_NODES, _LEVEL_SKILLS, _MARKET, _NODE_TO_FAMILY
    if _GRAPH_NODES:
        return

    try:
        raw = json.loads((_DATA_DIR / "graph.json").read_text(encoding="utf-8"))
        _GRAPH_NODES = {n["node_id"]: n for n in raw.get("nodes", [])}
    except Exception as e:
        logger.warning("graph.json load failed: %s", e)

    try:
        _LEVEL_SKILLS = json.loads((_DATA_DIR / "level_skills.json").read_text(encoding="utf-8"))
    except Exception:
        pass  # optional — fallback to gap_skills

    try:
        raw_market = json.loads((_DATA_DIR / "market_signals.json").read_text(encoding="utf-8"))
        _MARKET = raw_market if isinstance(raw_market, dict) else {}
        for family, info in _MARKET.items():
            for nid in info.get("node_ids", []):
                _NODE_TO_FAMILY[nid] = family
        # Fallback: nodes missing from market_signals → alias to nearest family
        _FAMILY_ALIASES = {
            "systems-cpp": "cpp",   # 系统C++归属系统编程族
        }
        for node, alias in _FAMILY_ALIASES.items():
            if node not in _NODE_TO_FAMILY and alias in _NODE_TO_FAMILY:
                _NODE_TO_FAMILY[node] = _NODE_TO_FAMILY[alias]
    except Exception as e:
        logger.warning("market_signals.json load failed: %s", e)


# ── Getter functions (sub-modules must use these instead of direct imports) ───

def get_graph_nodes() -> dict[str, dict]:
    _load_static()
    return _GRAPH_NODES


def get_level_skills() -> dict[str, dict]:
    _load_static()
    return _LEVEL_SKILLS


def get_market() -> dict[str, dict]:
    _load_static()
    return _MARKET


def get_node_to_family() -> dict[str, str]:
    _load_static()
    return _NODE_TO_FAMILY


def get_skill_fill_path_cache() -> dict[str, str]:
    return _load_skill_fill_path_cache()
