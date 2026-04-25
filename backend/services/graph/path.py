# -*- coding: utf-8 -*-
"""Path-finding helpers for career transition routes."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


# ── Family group mapping (from escape_router.py) ──────────────────────────
_FAMILY_GROUPS: dict[str, str] = {
    # English keys (legacy)
    "software_development": "tech",
    "algorithm_ai": "tech",
    "data_engineering": "tech",
    "data_analysis": "tech",
    "devops_infra": "tech",
    "quality_assurance": "tech",
    "embedded_hardware": "tech",
    "product_design": "design",
    "creative": "design",
    "management": "business",
    "sales_marketing": "business",
    "hr_admin": "business",
    "finance": "business",
    "education": "service",
    "healthcare": "service",
    "legal": "service",
    "public_service": "service",
    "manufacturing": "industry",
    "delivery_and_support": "service",
    "other": "other",
    # Chinese keys (matching graph.json role_family)
    "后端开发": "tech",
    "前端开发": "tech",
    "全栈开发": "tech",
    "移动开发": "tech",
    "AI/ML": "tech",
    "数据": "tech",
    "运维/DevOps": "tech",
    "系统开发": "tech",
    "系统软件": "tech",
    "嵌入式/硬件": "tech",
    "区块链": "tech",
    "安全": "tech",
    "质量保障": "tech",
    "架构": "tech",
    "游戏开发": "tech",
    "设计": "design",
    "产品": "business",
    "管理": "business",
    "文档": "service",
    "社区": "service",
}


# ── Direction modifier matrix (asymmetric transition costs) ───────────────
_DIRECTION_MODIFIER: dict[tuple[str, str], float] = {
    # tech ->
    ("tech", "tech"): 1.0,
    ("tech", "design"): 1.1,
    ("tech", "business"): 0.85,
    ("tech", "service"): 0.7,
    ("tech", "industry"): 0.9,
    # design ->
    ("design", "tech"): 1.3,
    ("design", "design"): 1.0,
    ("design", "business"): 1.0,
    ("design", "service"): 0.8,
    ("design", "industry"): 1.2,
    # business ->
    ("business", "tech"): 1.4,
    ("business", "design"): 1.2,
    ("business", "business"): 1.0,
    ("business", "service"): 0.8,
    ("business", "industry"): 1.1,
    # service ->
    ("service", "tech"): 1.8,
    ("service", "design"): 1.5,
    ("service", "business"): 1.3,
    ("service", "service"): 1.0,
    ("service", "industry"): 1.1,
    # industry ->
    ("industry", "tech"): 1.3,
    ("industry", "design"): 1.3,
    ("industry", "business"): 1.0,
    ("industry", "service"): 0.85,
    ("industry", "industry"): 1.0,
}


# ── Internal dataclasses ─────────────────────────────────────────────────

@dataclass
class _GapSkill:
    """A single gap skill with estimated learning hours."""
    name: str
    estimated_hours: int = 40


@dataclass(order=True)
class _SearchState:
    """Dijkstra priority queue node for escape route search."""
    cost: float
    node_id: str = field(compare=False)
    path: list[str] = field(compare=False)
    hops: int = field(compare=False)


# ── Helper functions (migrated from escape_router.py) ────────────────────

def _cross_family_distance(family_a: str, family_b: str) -> float:
    """Cross-family penalty: same=0, same_group=0.3, adjacent=0.6, far=1.0"""
    if family_a == family_b:
        return 0.0
    group_a = _FAMILY_GROUPS.get(family_a, "other")
    group_b = _FAMILY_GROUPS.get(family_b, "other")
    if group_a == group_b:
        return 0.3
    # tech<->design, business<->service, tech<->business are adjacent
    adjacent = {
        frozenset({"tech", "design"}),
        frozenset({"business", "service"}),
        frozenset({"tech", "business"}),
    }
    if frozenset({group_a, group_b}) in adjacent:
        return 0.6
    return 1.0


def _compute_gap_skills(
    current: dict, target: dict, edge: dict | None = None,
    profile_skills: list[str] | None = None,
) -> list[_GapSkill]:
    """Compute skill gaps. Uses user's actual skills when available, then node skills as fallback."""
    # Prefer edge data (more precise)
    if edge and edge.get("gap_skills"):
        edge_hours = edge.get("transition_hours", 80)
        gap_count = len(edge["gap_skills"])
        per_skill_hours = max(20, edge_hours // max(1, gap_count))
        raw_gaps = edge["gap_skills"]
        # Filter out skills user already has
        if profile_skills:
            user_set = set(s.lower() for s in profile_skills)
            raw_gaps = [g for g in raw_gaps if g.lower() not in user_set]
        return [_GapSkill(name=s, estimated_hours=per_skill_hours) for s in raw_gaps]

    # Fallback: skill set difference — use user's actual skills when available
    if profile_skills:
        user_skills = set(s.lower() for s in profile_skills)
    else:
        user_skills = set(s.lower() for s in current.get("must_skills", []))
    target_skills_raw = target.get("must_skills", [])
    target_skills = set(s.lower() for s in target_skills_raw)
    gap_names = target_skills - user_skills
    # Preserve original casing from target
    gaps = [s for s in target_skills_raw if s.lower() in gap_names]
    return [_GapSkill(name=s, estimated_hours=40) for s in sorted(gaps)]


def _safety_score(node: dict) -> float:
    """Compute safety score: human_premium - ai_exposure (with DB fallback)."""
    hp = node.get("human_ai_leverage") or node.get("human_premium") or 50
    rp = node.get("replacement_pressure") or node.get("ai_exposure") or 50
    return float(hp) - float(rp)


def _edge_cost(
    from_node: dict,
    to_node: dict,
    edge: dict,
) -> float:
    """
    4-factor weighted transition cost:

    cost = 0.40 x skill_gap_cost
         + 0.25 x cross_family_penalty
         + 0.20 x seniority_cost
         + 0.15 x danger_zone_penalty
    """
    # Factor 1: Skill gap cost (0~1)
    gap_skills = _compute_gap_skills(from_node, to_node, edge)
    gap_hours = sum(s.estimated_hours for s in gap_skills)
    # Normalize: 0 hours = 0, 200+ hours = 1
    skill_cost = min(1.0, gap_hours / 200.0)

    # Factor 2: Cross-family penalty (0~1)
    family_a = from_node.get("role_family", "other")
    family_b = to_node.get("role_family", "other")
    category_cost = _cross_family_distance(family_a, family_b)

    # Factor 3: Seniority span penalty (0~1)
    sal_a = from_node.get("salary_p50") or 10000
    sal_b = to_node.get("salary_p50") or 10000
    # Log distance of salary ratio, normalized to 0~1
    seniority_cost = min(1.0, abs(math.log(max(sal_b, 1) / max(sal_a, 1))) / 1.5)

    # Factor 4: Danger zone transit penalty (0 or 1)
    to_zone = to_node.get("zone", "transition")
    danger_cost = 1.0 if to_zone == "danger" else (0.3 if to_zone == "transition" else 0.0)

    # Weighted sum + direction modifier
    raw_cost = (
        0.40 * skill_cost
        + 0.25 * category_cost
        + 0.20 * seniority_cost
        + 0.15 * danger_cost
    )
    group_a = _FAMILY_GROUPS.get(family_a, "other")
    group_b = _FAMILY_GROUPS.get(family_b, "other")
    direction_mod = _DIRECTION_MODIFIER.get((group_a, group_b), 1.0)
    return raw_cost * direction_mod
