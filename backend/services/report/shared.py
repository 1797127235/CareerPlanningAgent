# -*- coding: utf-8 -*-
"""Shared utilities for report service sub-modules."""
from __future__ import annotations

import json
import logging
import math
from typing import Any

logger = logging.getLogger(__name__)


_PROJECT_SKILL_HINTS: dict[str, list[str]] = {
    "性能优化": ["性能", "高性能", "压测", "benchmark", "qps", "延迟", "吞吐", "profile", "热点", "优化"],
    "高并发":   ["并发", "高并发", "多线程", "线程池", "epoll", "reactor", "内存池", "qps", "压测"],
    "系统编程": ["系统编程", "系统调用", "内核", "epoll", "reactor", "内存池", "多线程", "linux系统", "io_uring"],
    "网络编程": ["网络", "socket", "tcp", "epoll", "reactor", "网络库", "网络框架", "tcp/ip"],
    "内存管理": ["内存", "内存池", "tcmalloc", "jemalloc", "malloc", "分配器", "cache"],
    "GDB":      ["gdb", "调试", "core dump", "断点"],
    "CMake":    ["cmake", "makefile", "构建", "编译系统"],
    "Linux":    ["linux", "系统调用", "epoll", "内核", "posix", "linux网络"],
    "STL":      ["stl", "标准库", "容器", "迭代器", "模板", "vector", "map", "智能指针", "shared_ptr", "unique_ptr"],
    "多线程":   ["多线程", "线程池", "并发", "锁", "mutex", "原子操作", "thread"],
    "C++":      ["c++", "cpp", "stl", "模板", "虚函数", "raii", "智能指针"],
    "TCP/IP":   ["tcp", "tcp/ip", "socket", "网络协议", "三次握手", "epoll", "网络库"],
    "数据结构": ["数据结构", "链表", "红黑树", "哈希", "b+树", "跳表", "队列", "堆"],
    "操作系统": ["操作系统", "进程", "线程", "虚拟内存", "页表", "调度", "信号", "文件系统"],
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
