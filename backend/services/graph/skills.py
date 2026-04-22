"""Skill vocabulary extraction from graph and user text."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from backend.services.graph.query import _get_graph_nodes

logger = logging.getLogger(__name__)

_GRAPH_SKILL_TOKENS_CACHE: set[str] | None = None
_skill_vocab_cache: str | None = None

# ── Text-scanned skill vocabulary ────────────────────────────────────────────

_GRAPH_SKILL_TOKENS_CACHE: set[str] | None = None


def _build_graph_skill_tokens() -> set[str]:
    """Build tokenized skill vocabulary from all graph node must_skills.

    Returns lowercase tokens/phrases that can be searched for in resume text.
    Includes both full skill names and individual tokens split by separators,
    plus 2-character prefixes for pure-Chinese phrases so that e.g.
    "缺陷管理" produces "缺陷" which can match text mentioning "缺陷".
    """
    global _GRAPH_SKILL_TOKENS_CACHE
    if _GRAPH_SKILL_TOKENS_CACHE is not None:
        return _GRAPH_SKILL_TOKENS_CACHE
    graph_nodes = _get_graph_nodes()
    tokens: set[str] = set()
    for node in graph_nodes.values():
        for s in node.get("must_skills", []):
            if not s or not s.strip():
                continue
            sl = s.strip().lower()
            tokens.add(sl)
            normalized = sl
            for sep in ["/", "&", "、", "，", "(", ")", "（", "）", " "]:
                normalized = normalized.replace(sep, "|")
            for token in normalized.split("|"):
                token = token.strip()
                if token and len(token) >= 2:
                    tokens.add(token)
            # For pure Chinese phrases (e.g. "缺陷管理"), also add the
            # first 2 chars as a prefix token so "缺陷" hits "缺陷管理".
            if len(sl) >= 4 and all("\u4e00" <= c <= "\u9fff" for c in sl):
                tokens.add(sl[:2])
    _GRAPH_SKILL_TOKENS_CACHE = tokens
    return tokens


def _expand_chinese_tokens(phrases: list[str]) -> set[str]:
    """Expand phrases with Chinese prefix/bigram tokens for robust matching.

    Pure-Chinese phrases (e.g. '缺陷管理', '性能测试') have no separators,
    so exact substring matching misses them when user text only contains
    the prefix (e.g. '缺陷' instead of '缺陷管理').
    """
    expanded: set[str] = set()
    for p in phrases:
        p = p.strip().lower()
        if not p or len(p) < 2:
            continue
        expanded.add(p)
        # Split by separators (same as _node_skill_set)
        for sep in ["/", "&", "、", "，", "(", ")", "（", "）", " "]:
            p = p.replace(sep, "|")
        for token in p.split("|"):
            token = token.strip()
            if token and len(token) >= 2:
                expanded.add(token)
        # For pure Chinese phrases, add all prefix n-grams (len>=2)
        original = p.replace("|", "")
        if len(original) >= 4 and all("\u4e00" <= c <= "\u9fff" for c in original):
            for i in range(2, len(original)):
                expanded.add(original[:i])
    return expanded


def _extract_implied_skills_from_text(profile_data: dict) -> set[str]:
    """Scan resume text for graph skill vocabulary mentions.

    Dynamically discovers skill signals from raw_text, projects, internships,
    and work experiences without hard-coding tool→skill mappings.
    """
    parts: list[str] = []

    raw_text = (profile_data.get("raw_text") or "").lower()
    if raw_text:
        parts.append(raw_text)

    for proj in profile_data.get("projects", []):
        if isinstance(proj, dict):
            parts.append(str(proj.get("name", "")).lower())
            parts.append(str(proj.get("description", "") or proj.get("highlights", "")).lower())
        elif isinstance(proj, str):
            parts.append(proj.lower())

    for intern in profile_data.get("internships", []):
        if isinstance(intern, dict):
            parts.append(str(intern.get("role", "")).lower())
            parts.append(str(intern.get("description", "") or intern.get("highlights", "")).lower())
        elif isinstance(intern, str):
            parts.append(intern.lower())

    for work in profile_data.get("work_experiences", []):
        if isinstance(work, dict):
            parts.append(str(work.get("description", "")).lower())
        elif isinstance(work, str):
            parts.append(work.lower())

    combined = " ".join(parts)
    if not combined.strip():
        return set()

    tokens = _build_graph_skill_tokens()
    implied: set[str] = set()
    for token in tokens:
        if len(token) < 2:
            continue
        if token in combined:
            implied.add(token)
    return implied


def _build_work_content_summary(profile_data: dict) -> str:
    """Generate a summary of work-content keywords from user text.

    Scans all graph node core_tasks against user project/internship/raw_text
    and returns a sentence listing the most frequently matched task tokens.
    This gives the LLM an objective, data-driven signal of what the user
    actually does (as opposed to what skills they claim to have).
    """
    parts: list[str] = []
    rt = (profile_data.get("raw_text") or "").lower()
    if rt:
        parts.append(rt)
    for p in profile_data.get("projects", []):
        if isinstance(p, dict):
            parts.append(str(p.get("name", "")).lower())
            parts.append(str(p.get("description", "") or p.get("highlights", "")).lower())
        elif isinstance(p, str):
            parts.append(p.lower())
    for i in profile_data.get("internships", []):
        if isinstance(i, dict):
            parts.append(str(i.get("role", "")).lower())
            parts.append(str(i.get("description", "") or i.get("highlights", "")).lower())
        elif isinstance(i, str):
            parts.append(i.lower())
    user_text = " ".join(parts)
    if not user_text.strip():
        return "未提取到工作内容关键词"

    graph_nodes = _get_graph_nodes()
    # Collect all core_tasks, count hits
    task_hits: dict[str, int] = {}
    for node in graph_nodes.values():
        for t in node.get("core_tasks", []):
            if not t or len(t.strip()) < 3:
                continue
            expanded = _expand_chinese_tokens([t])
            for token in expanded:
                if len(token) >= 2 and token in user_text:
                    task_hits[token] = task_hits.get(token, 0) + 1

    if not task_hits:
        return "未提取到工作内容关键词"

    # Sort by hit count, keep top unique tokens (prefer longer phrases)
    sorted_tokens = sorted(task_hits.items(), key=lambda x: (-x[1], -len(x[0])))
    seen_roots: set[str] = set()
    unique: list[str] = []
    for token, count in sorted_tokens:
        # Skip if a shorter version is already included (e.g. skip "测试" if "测试用例" is in)
        if any(token in u and token != u for u in unique):
            continue
        unique.append(token)
        if len(unique) >= 8:
            break

    return "、".join(unique)
def _build_skill_vocab() -> str:
    """Collect all unique must_skills from graph as standard vocabulary (module-level cached)."""
    global _skill_vocab_cache
    if _skill_vocab_cache is not None:
        return _skill_vocab_cache
    graph_nodes = _get_graph_nodes()
    all_skills: set[str] = set()
    for n in graph_nodes.values():
        for s in n.get("must_skills", []):
            all_skills.add(s)
    _skill_vocab_cache = ", ".join(sorted(all_skills))
    return _skill_vocab_cache
