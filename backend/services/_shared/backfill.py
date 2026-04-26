"""Shared backfill scoring logic for graph recommendations."""

from __future__ import annotations


def compute_backfill_candidates(
    graph_nodes: dict,
    user_skill_set: set[str],
    user_text_combined: str,
    existing_ids: set[str],
    exp_years: int,
    expand_fn,
) -> list[tuple]:
    """Score all graph nodes for backfill and return sorted candidates.

    Args:
        graph_nodes: Dict of node_id -> node dict.
        user_skill_set: Set of normalized user skills.
        user_text_combined: Lowercase combined text from projects/internships.
        existing_ids: Set of node_ids already in recommendations (to exclude).
        exp_years: User experience years (for seniority filtering).
        expand_fn: Function to expand Chinese tokens (e.g. _expand_chinese_tokens).

    Returns list of tuples: (total_score, overlap, task_hits, nid, node)
    sorted by total_score descending.
    """
    candidates = []
    for nid, node in graph_nodes.items():
        if nid in existing_ids:
            continue
        cl = node.get("career_level", 0) or 0
        if exp_years == 0 and cl > 3:
            continue
        if exp_years <= 1 and cl > 4:
            continue
        raw_skills = [
            (s if isinstance(s, str) else s.get("name", "")).lower().strip()
            for s in (node.get("must_skills") or [])
        ]
        expanded_skills = expand_fn(raw_skills)
        overlap = len(user_skill_set & expanded_skills)
        core_tasks = [
            t.strip() for t in node.get("core_tasks", []) if t and len(t.strip()) >= 3
        ]
        expanded_tasks = expand_fn(core_tasks)
        task_hits = (
            sum(1 for t in expanded_tasks if len(t) >= 2 and t in user_text_combined)
            if core_tasks
            else 0
        )
        total_score = overlap + task_hits * 2
        if total_score == 0:
            continue
        candidates.append((total_score, overlap, task_hits, nid, node))
    candidates.sort(key=lambda x: -x[0])
    return candidates


def build_backfill_rec(
    total_score: int,
    overlap: int,
    task_hits: int,
    nid: str,
    node: dict,
) -> dict:
    """Build a single backfill recommendation dict from scored candidate."""
    base_affinity = min(60 + total_score * 5, 78)
    reason_parts = []
    if overlap:
        reason_parts.append(f"技能画像与该方向有 {overlap} 项重合")
    if task_hits:
        reason_parts.append(f"项目/实习经历与该岗位核心任务有 {task_hits} 项匹配")
    return {
        "role_id": nid,
        "label": node.get("label", nid),
        "affinity_pct": base_affinity,
        "matched_skills": [],
        "gap_skills": (node.get("must_skills") or [])[:4],
        "gap_hours": 0,
        "zone": node.get("zone", "safe"),
        "salary_p50": node.get("salary_p50", 0),
        "reason": "；".join(reason_parts) or f"技能画像与该方向有 {overlap} 项重合",
        "channel": "growth",
        "career_level": node.get("career_level", 0),
        "replacement_pressure": node.get("replacement_pressure", 50),
        "human_ai_leverage": node.get("human_ai_leverage", 50),
    }
