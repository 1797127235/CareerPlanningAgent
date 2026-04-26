"""Shared recommendation building utilities."""

from __future__ import annotations

from backend.services.graph.matching import find_role_id_for_job_target


def apply_job_target_override(
    recs: list[dict],
    job_target: str,
    graph_nodes: dict,
    *,
    min_affinity: int = 88,
    boost_above_top: bool = False,
) -> list[dict]:
    """Force job_target role to rank #1 in recommendations.

    If the target role already exists in recs, it is moved to position 0
    and its affinity is boosted to at least ``min_affinity``.
    If it doesn't exist, a new record is inserted at position 0.

    Args:
        recs: Existing recommendation list (will be mutated).
        job_target: Raw job target string from user profile.
        graph_nodes: Dict of node_id -> node dict.
        min_affinity: Floor affinity for the target role.
        boost_above_top: If True, boost to max(min_affinity, top_existing_affinity + 5).
                         Used by the recommendations router.
    """
    target_role_id = find_role_id_for_job_target(job_target)
    if not target_role_id or target_role_id not in graph_nodes:
        return recs

    existing_ids = [r["role_id"] for r in recs]
    top_affinity = max((r.get("affinity_pct", 0) for r in recs), default=60)

    if boost_above_top:
        target_affinity = max(min(99, top_affinity + 5), min_affinity)
    else:
        target_affinity = min_affinity

    if target_role_id in existing_ids:
        idx = existing_ids.index(target_role_id)
        target_rec = recs.pop(idx)
        target_rec["affinity_pct"] = max(
            target_rec.get("affinity_pct", 0), target_affinity
        )
        target_rec["channel"] = "entry"
        target_rec["reason"] = (
            target_rec.get("reason") or f"与求职意向「{job_target}」高度吻合"
        )
        recs.insert(0, target_rec)
    else:
        node = graph_nodes[target_role_id]
        recs.insert(
            0,
            {
                "role_id": target_role_id,
                "label": node.get("label", target_role_id),
                "affinity_pct": target_affinity,
                "matched_skills": [],
                "gap_skills": node.get("must_skills", [])[:4],
                "gap_hours": 0,
                "zone": node.get("zone", "safe"),
                "salary_p50": node.get("salary_p50", 0),
                "reason": f"与求职意向「{job_target}」高度吻合",
                "channel": "entry",
                "career_level": node.get("career_level", 0),
                "replacement_pressure": node.get("replacement_pressure", 50),
                "human_ai_leverage": node.get("human_ai_leverage", 50),
            },
        )

    return recs
