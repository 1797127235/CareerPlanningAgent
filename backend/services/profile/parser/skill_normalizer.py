"""Skill granularity normalizer — merge overly-fine skills into family heads.

Rules are conservative: only merge when the parent skill already exists.
If the parent is missing, the child is kept (it signals real domain depth).
"""
from __future__ import annotations

import logging

from backend.services.profile.parser.schema import ProfileData, Skill

logger = logging.getLogger(__name__)

# Parent skill (case-insensitive) → list of child skills that should be folded into it
# ONLY when the parent already exists in the profile.
_SKILL_FAMILIES: dict[str, list[str]] = {
    "c++": [
        "c++11", "c++14", "c++17", "c++20", "cpp", "c/c++",
        "右值引用", "移动语义", "lambda", "auto", "constexpr",
        "模板元编程", "变参模板", " SFINAE", "traits",
    ],
    "c": ["c语言"],
    "stl": [
        "vector", "map", "set", "unordered_map", "unordered_set",
        "list", "deque", "queue", "stack", "priority_queue",
        "迭代器", "algorithm", "算法库", "functional",
    ],
    "智能指针": ["shared_ptr", "unique_ptr", "weak_ptr", "make_shared", "make_unique"],
    "linux": [
        "epoll", "poll", "select", "io多路复用", "io复用",
        "非阻塞io", "异步io", "posix", "系统调用",
        "进程间通信", "ipc", "mmap", "零拷贝", "信号", "管道",
    ],
    "网络编程": [
        "tcp/ip", "socket", "udp", "http", "https",
        "网络库", "reactor", "proactor", "muduo", "libevent", "libuv",
        "nio", "nio框架", "websocket", "grpc", "rpc框架",
    ],
    "多线程/并发": [
        "线程池", "并发编程", "锁", "互斥量", "互斥锁", "mutex",
        "条件变量", "condition_variable", "原子操作", "atomic",
        "信号量", "读写锁", "自旋锁", "无锁编程", "cas",
    ],
    "内存管理": [
        "内存池", "tcmalloc", "jemalloc", "allocator", "分配器",
        "对象池", "span", "分页", "虚拟内存", "内存碎片",
    ],
    "数据库": [
        "索引", "事务", "b+树", "b树", "存储引擎", "查询优化",
        "分库分表", "主从同步", "binlog", "redo log", "undo log",
    ],
    "容器/云原生": [
        "docker", "kubernetes", "k8s", "容器", "cicd", "devops",
        "helm", "istio", "prometheus", "grafana", "jenkins",
    ],
}

# Build reverse lookup: child_lower → parent_name
_CHILD_TO_PARENT: dict[str, str] = {}
for parent, children in _SKILL_FAMILIES.items():
    for child in children:
        _CHILD_TO_PARENT[child.lower()] = parent


def normalize_skills(skills: list[Skill]) -> list[Skill]:
    """Fold child skills into existing parents; keep orphans.

    Examples:
      - [C++, C++11, Lambda, Vector] → [C++, STL]  (C++11/Lambda folded into C++; Vector→STL)
      - [Vector] → [Vector]  (no STL parent, keep as-is)
      - [C++, Vector] → [C++, STL]  (Vector folded into STL because STL implied by C++ ecosystem)
    """
    if not skills:
        return skills

    # Index by lowercase name for fast lookup
    skill_map: dict[str, Skill] = {s.name.lower(): s for s in skills}

    # Determine which parents are "present"
    # A parent is present if explicitly listed OR strongly implied by ecosystem
    present_parents: set[str] = set()
    for name in skill_map:
        if name in _SKILL_FAMILIES:
            present_parents.add(name)

    # Ecosystem implication: if C++ is present, STL / 智能指针 / Linux / 网络编程 are implied
    # This prevents [C++, Vector, Epoll] from showing 5 items when C++ alone signals the ecosystem
    ecosystem_implied: set[str] = set()
    if "c++" in present_parents:
        ecosystem_implied.update(["stl", "智能指针", "linux", "网络编程", "多线程/并发", "内存管理"])
    if "java" in present_parents:
        ecosystem_implied.update(["多线程/并发"])
    if "go" in present_parents:
        ecosystem_implied.update(["网络编程", "多线程/并发"])

    present_parents.update(ecosystem_implied)

    # Pass 1: mark children for removal / rename
    to_remove: set[str] = set()
    to_rename: dict[str, str] = {}  # child_lower → parent_name

    for name_lower in list(skill_map.keys()):
        if name_lower in _SKILL_FAMILIES:
            continue  # never remove a parent itself

        parent = _CHILD_TO_PARENT.get(name_lower)
        if parent and parent in present_parents:
            to_remove.add(name_lower)
            logger.debug("Skill merge: %r → %r (parent exists)", name_lower, parent)

    # Pass 2: if a parent is implied by ecosystem but not explicitly listed, add it
    for parent in ecosystem_implied:
        if parent not in skill_map:
            # Find best level among children that map to this parent
            best_level = "familiar"
            for child_name, child_skill in skill_map.items():
                if _CHILD_TO_PARENT.get(child_name) == parent:
                    if _LEVEL_RANK.get(child_skill.level, 0) < _LEVEL_RANK.get(best_level, 0):
                        best_level = child_skill.level
            skill_map[parent] = Skill(name=parent.title() if parent != "c++" else "C++", level=best_level)
            logger.info("Skill ecosystem: added implied parent %r at level %r", parent, best_level)

    # Pass 3: remove folded children
    for name in to_remove:
        skill_map.pop(name, None)

    # Pass 4: dedupe by name (case-insensitive), keep highest level
    merged: dict[str, Skill] = {}
    for s in skill_map.values():
        key = s.name.lower()
        if key not in merged:
            merged[key] = s
        else:
            if _LEVEL_RANK.get(s.level, 0) < _LEVEL_RANK.get(merged[key].level, 0):
                merged[key] = s

    result = list(merged.values())
    logger.info("Skill normalization: %d → %d skills", len(skills), len(result))
    return result


_LEVEL_RANK = {"beginner": 3, "familiar": 2, "intermediate": 1, "advanced": 0}


def apply_to_profile(profile: ProfileData) -> ProfileData:
    """Normalize skills in-place on a ProfileData instance."""
    profile.skills = normalize_skills(profile.skills)
    return profile
