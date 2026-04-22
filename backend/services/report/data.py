# -*- coding: utf-8 -*-
"""Static data loaders and shared utilities for report service."""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"

# ── Static data (loaded once per process) ───────────────────────────────────

_GRAPH_NODES: dict[str, dict] = {}
_LEVEL_SKILLS: dict[str, dict] = {}
_MARKET: dict[str, dict] = {}        # family_name -> signal dict
_NODE_TO_FAMILY: dict[str, str] = {} # node_id -> family_name

_SKILL_FILL_PATH_PATH = _PROJECT_ROOT / "data" / "skill_fill_path_tags.json"
_SKILL_FILL_PATH_CACHE: dict[str, str] | None = None

# Career-alignment graph cache (auto-invalidates on mtime change)
_graph_cache: list[dict] | None = None
_graph_mtime: float = 0.0



_PROJECT_SKILL_HINTS: dict[str, list[str]] = {
    "性能优化": ["性能", "高性能", "压测", "benchmark", "qps", "延迟", "吞吐", "profile", "热点", "优化"],
    "高并发":   ["并发", "高并发", "多线程", "线程池", "epoll", "reactor", "内存池", "qps", "压测"],
    "系统编程": ["系统编程", "系统调用", "内核", "epoll", "reactor", "内存池", "多线程", "linux系统", "io_uring"],
    "网络编程": ["网络", "socket", "tcp", "epoll", "reactor", "网络库", "网络框架"],
    "内存管理": ["内存", "内存池", "tcmalloc", "jemalloc", "malloc", "分配器"],
    "GDB":      ["gdb", "调试", "core dump", "断点"],
    "CMake":    ["cmake", "makefile", "构建", "编译系统"],
    "Linux":    ["linux", "系统调用", "epoll", "内核", "posix"],
    "STL":      ["stl", "标准库", "容器", "迭代器", "模板"],
    "多线程":   ["多线程", "线程池", "并发", "锁", "mutex", "原子操作"],
    "C++":      ["c++", "cpp", "stl", "模板", "虚函数"],
}

_PROFICIENCY_MULTIPLIER = {"completed": 1.2, "practiced": 1.0, "claimed": 0.7}


def _norm_skill(s: str) -> str:
    return s.lower().strip().replace(" ", "").replace("-", "").replace("_", "")


def _user_skill_set(profile_data: dict) -> set[str]:
    raw = profile_data.get("skills", [])
    if not raw:
        return set()
    if isinstance(raw[0], dict):
        return {s.get("name", "").lower().strip() for s in raw if s.get("name")}
    return {s.lower().strip() for s in raw if isinstance(s, str) and s.strip()}


def _skill_matches(skill_name: str, user_skills: set[str]) -> bool:
    """Reuse same matching logic as growth_log_service."""
    name = skill_name.lower().strip()
    name_norm = _norm_skill(skill_name)
    if not name:
        return False
    if name in user_skills:
        return True
    if len(name_norm) <= 2:
        return False
    for us in user_skills:
        if not us:
            continue
        us_norm = _norm_skill(us)
        if name_norm == us_norm:
            return True
        if len(us_norm) > 2 and (name_norm in us_norm or us_norm in name_norm):
            return True
    return False


def _skill_in_set(skill_name: str, skill_set: set[str]) -> bool:
    """Fuzzy-check whether skill_name appears in a given set (e.g. practiced skills from projects)."""
    if not skill_set:
        return False
    name_norm = _norm_skill(skill_name)
    if not name_norm:
        return False
    for s in skill_set:
        s_norm = _norm_skill(s)
        if name_norm == s_norm:
            return True
        if len(name_norm) > 2 and len(s_norm) > 2 and (name_norm in s_norm or s_norm in name_norm):
            return True
    return False


def _skill_proficiency(
    skill_name: str,
    user_skills: set[str],
    practiced: set[str],
    completed_practiced: set[str],
    has_project_data: bool,
) -> tuple[bool, str | None]:
    """
    Returns (is_matched, status):
      status = 'completed'  — used in a completed project (weight 1.2×)
             = 'practiced'  — used in any project (weight 1.0×)
             = 'claimed'    — resume only, not verified in projects (weight 0.7×)
             = None         — user doesn't have this skill
    When has_project_data is False (fresh student), matched skills get 'claimed'
    without the 0.7× penalty so new students aren't penalised.
    """
    # Project evidence takes priority: if the skill is demonstrated in projects,
    # it counts as matched even if the user didn't explicitly list it in skills.
    if has_project_data:
        if _skill_in_set(skill_name, completed_practiced):
            return True, "completed"
        if _skill_in_set(skill_name, practiced):
            return True, "practiced"

    if not _skill_matches(skill_name, user_skills):
        return False, None
    if not has_project_data:
        return True, "claimed"
    return True, "claimed"


def _cosine_sim(a: list[float], b: list[float]) -> float:
    """Pure-Python cosine similarity (no numpy dependency)."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _batch_embed(texts: list[str]) -> list[list[float]] | None:
    """
    Batch-embed a list of texts via DashScope text-embedding-v3.
    Returns list of embedding vectors, or None on failure.

    DashScope 限制单次 batch ≤ 10 条，超出会 400 InvalidParameter。
    这里按 10 个一组切片并顺序调用，结果按原顺序拼接。
    """
    if not texts:
        return []
    try:
        from backend.llm import get_llm_client
        client = get_llm_client(timeout=60)
        _CHUNK = 10
        out: list[list[float]] = []
        for i in range(0, len(texts), _CHUNK):
            chunk = texts[i : i + _CHUNK]
            resp = client.embeddings.create(
                model="text-embedding-v3",
                input=chunk,
            )
            ordered = sorted(resp.data, key=lambda d: d.index)
            out.extend(d.embedding for d in ordered)
        return out
    except Exception as e:
        logger.warning("_batch_embed failed: %s", e)
        return None

# ── Data loaders ────────────────────────────────────────────────────────────


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