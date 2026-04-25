# -*- coding: utf-8 -*-
"""GraphService — unified graph access layer."""
from __future__ import annotations

import heapq
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

import networkx as nx
from sqlalchemy.orm import Session

from backend.services.graph.path import (
    _FAMILY_GROUPS,
    _GapSkill,
    _SearchState,
    _compute_gap_skills,
    _cross_family_distance,
    _edge_cost,
    _safety_score,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DEFAULT_GRAPH_PATH = _PROJECT_ROOT / "data" / "graph.json"

_DIFF_WEIGHT = {"低": 1.0, "中": 2.0, "高": 3.0}


class GraphService:
    """Unified graph access layer — loads, queries, and computes over the career graph."""

    def __init__(self, graph_path: Path | str | None = None):
        self._graph_path = Path(graph_path) if graph_path else _DEFAULT_GRAPH_PATH
        self._graph: nx.DiGraph | None = None
        self._nodes: dict[str, dict[str, Any]] = {}
        self._adj: dict[str, list[tuple[str, dict]]] = {}
        self._label_index: dict[str, str] = {}  # label -> node_id

    # ------------------------------------------------------------------
    # load / info / properties
    # ------------------------------------------------------------------

    def load(self, db_session: Session | None = None) -> None:
        """Load graph.json into NetworkX DiGraph, merge DB scores if available."""
        if self._graph is not None:
            return  # already loaded (singleton cache)

        raw = json.loads(self._graph_path.read_text(encoding="utf-8"))
        self._graph = nx.DiGraph()
        self._nodes = {}
        self._adj = {}
        self._label_index = {}

        for n in raw.get("nodes", []):
            nid = n["node_id"]
            self._nodes[nid] = n
            self._graph.add_node(nid, **n)
            self._label_index[n.get("label", nid)] = nid

        for e in raw.get("edges", []):
            src, tgt = e["source"], e["target"]
            weight = _DIFF_WEIGHT.get(e.get("difficulty", "中"), 2.0)
            self._graph.add_edge(src, tgt, weight=weight, **e)

        # Build adjacency list (bidirectional, for escape route search)
        self._adj = {nid: [] for nid in self._nodes}
        for e in raw.get("edges", []):
            src, tgt = e.get("source", ""), e.get("target", "")
            if src in self._adj:
                self._adj[src].append((tgt, e))
            if tgt in self._adj:
                self._adj[tgt].append((src, e))

        logger.info("Graph loaded: %d nodes, %d edges", len(self._nodes), self._graph.number_of_edges())

        # Overlay DB scores onto nodes (if session provided)
        if db_session is not None:
            self._overlay_db_scores(db_session)

    def _overlay_db_scores(self, db_session: Session) -> None:
        """Merge terrain scores from job_scores table onto graph nodes."""
        try:
            from backend.models import JobScore
            for score in db_session.query(JobScore).all():
                if score.node_id in self._nodes:
                    self._nodes[score.node_id]["zone"] = score.zone
                    self._nodes[score.node_id]["replacement_pressure"] = score.replacement_pressure
                    self._nodes[score.node_id]["human_ai_leverage"] = score.human_ai_leverage
                    self._nodes[score.node_id]["runway_months"] = score.runway_months
        except Exception:
            pass  # DB overlay is best-effort; fallback to JSON fields

    @property
    def node_ids(self) -> list[str]:
        return list(self._nodes.keys())

    def info(self) -> dict[str, int]:
        """Return basic graph statistics."""
        g = self._graph
        if g is None:
            return {"node_count": 0, "edge_count": 0}
        return {
            "node_count": g.number_of_nodes(),
            "edge_count": g.number_of_edges(),
        }

    def _get_edges_with_type(self) -> list[tuple[str, str, str]]:
        """Return list of (source, target, edge_type) tuples."""
        if self._graph is None:
            return []
        return [
            (s, t, d.get("edge_type", "related"))
            for s, t, d in self._graph.edges(data=True)
        ]

    # ------------------------------------------------------------------
    # Node access
    # ------------------------------------------------------------------

    def get_node(self, node_id: str) -> dict | None:
        """Get a single node by node_id."""
        return self._nodes.get(node_id)

    def search_nodes(self, keyword: str) -> list[dict]:
        """Search nodes by keyword — tiered matching for relevance.

        Tier 1 (always): label, node_id — direct identity match.
        Tier 2 (>= 2 chars): must_skills, core_tasks — skill/task match.
        Tier 3 (>= 3 chars): topics, role_family — broad category match.

        Short queries (1 char) only search Tier 1 to avoid noise.
        """
        if not keyword:
            return []
        if self._graph is None:
            logger.warning("search_nodes called but graph not loaded — calling load()")
            self.load()
        logger.debug("search_nodes: keyword=%r, node_count=%d", keyword, len(self._nodes))
        kw = keyword.lower().strip()
        kw_len = len(kw)
        # Chinese characters count as 2 effective chars (more specific)
        effective_len = sum(2 if "一" <= c <= "鿿" else 1 for c in kw)

        tier1: list[dict] = []
        tier2: list[dict] = []
        tier3: list[dict] = []
        seen: set[str] = set()

        for node in self._nodes.values():
            nid = node.get("node_id", "")
            if nid in seen:
                continue

            # Tier 1: label + node_id (always searched)
            if kw in node.get("label", "").lower() or kw in nid.lower():
                tier1.append(node)
                seen.add(nid)
                continue

            # Tier 2: must_skills + core_tasks (need >= 2 effective chars)
            if effective_len >= 2:
                skills = node.get("must_skills", [])
                tasks = node.get("core_tasks", [])
                if (any(kw in s.lower() for s in skills)
                        or any(kw in t.lower() for t in tasks)):
                    tier2.append(node)
                    seen.add(nid)
                    continue

            # Tier 3: topics + role_family (need >= 3 effective chars)
            if effective_len >= 3:
                topics = node.get("topics", [])
                family = node.get("role_family", "")
                if (kw in family.lower()
                        or any(kw in t.lower() for t in topics)):
                    tier3.append(node)
                    seen.add(nid)
                    continue

        return tier1 + tier2 + tier3

    # ------------------------------------------------------------------
    # Escape routes (migrated from escape_router.py)
    # ------------------------------------------------------------------
    # Escape routes (migrated from escape_router.py)
    # ------------------------------------------------------------------

    def find_escape_routes(
        self,
        node_id: str,
        profile_skills: list[str] | None = None,
        db_session: Session | None = None,
        top_k: int = 3,
        max_hops: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Weighted Dijkstra escape route calculation.

        Returns top-3 routes with:
        {target, target_label, target_zone, path, total_cost,
         gap_skills, total_hours, safety_gain, salary_p50, tag}
        """
        if node_id not in self._nodes:
            return []

        # Overlay DB scores if session provided and not already merged
        if db_session is not None:
            self._overlay_db_scores(db_session)

        nodes = self._nodes
        adj = self._adj

        current = nodes[node_id]
        current_safety = _safety_score(current)

        # Dijkstra priority queue
        pq: list[_SearchState] = [
            _SearchState(cost=0.0, node_id=node_id, path=[], hops=0)
        ]
        best_cost: dict[str, float] = {node_id: 0.0}
        candidates: list[dict[str, Any]] = []

        while pq:
            state = heapq.heappop(pq)

            # Skip if we've found a better path
            if state.cost > best_cost.get(state.node_id, float("inf")):
                continue

            node = nodes.get(state.node_id)
            if not node:
                continue

            zone = node.get("zone", "transition")

            # Found a reachable destination — include all zones but prefer safe/leverage
            if state.node_id != node_id:
                # Filter out cross-group career jumps (e.g. QA -> management/architect)
                source_family = current.get("role_family", "other")
                target_family = node.get("role_family", "other")
                if _cross_family_distance(source_family, target_family) < 1.0:
                    src_skills = set(s.lower() for s in current.get("must_skills", []))
                    tgt_skills = set(s.lower() for s in node.get("must_skills", []))
                    has_overlap = bool(src_skills and tgt_skills and (src_skills & tgt_skills))
                    # For same-family or same-group routes: skip if zero skill overlap
                    # and no direct forward edge (unrelated sub-field)
                    if source_family == target_family or _FAMILY_GROUPS.get(source_family, "other") == _FAMILY_GROUPS.get(target_family, "other"):
                        if not has_overlap and not self._graph.has_edge(node_id, state.node_id):
                            continue
                    gap = _compute_gap_skills(current, node, profile_skills=profile_skills)
                    gap_hours = sum(s.estimated_hours for s in gap)
                    total_h = gap_hours if gap_hours > 0 else 40
                    candidates.append({
                        "target": state.node_id,
                        "target_label": node.get("label", state.node_id),
                        "target_zone": zone,
                        "path": state.path + [state.node_id],
                        "gap_skills": [{"name": g.name, "estimated_hours": g.estimated_hours} for g in gap],
                        "total_hours": total_h,
                        "safety_gain": round(_safety_score(node) - current_safety, 3),
                        "salary_p50": node.get("salary_p50") or 0,
                        "total_cost": round(state.cost, 3),
                        "tag": "",
                    })
                # Stop expanding from safe/leverage (stable endpoints); continue through danger/transition
                if zone in ("safe", "leverage"):
                    continue

            # Max hops reached
            if state.hops >= max_hops:
                continue

            # Expand neighbors
            for neighbor_id, edge in adj.get(state.node_id, []):
                neighbor = nodes.get(neighbor_id)
                if not neighbor:
                    continue

                # Compute weighted edge cost (4-factor)
                edge_c = _edge_cost(node, neighbor, edge)
                # Penalize reverse-direction edges (e.g. game-dev -> java becomes java -> game-dev)
                if edge.get("source") != state.node_id:
                    edge_c *= 1.5
                new_cost = state.cost + edge_c

                # Only expand if better
                if new_cost < best_cost.get(neighbor_id, float("inf")):
                    best_cost[neighbor_id] = new_cost
                    heapq.heappush(pq, _SearchState(
                        cost=new_cost,
                        node_id=neighbor_id,
                        path=state.path + [state.node_id],
                        hops=state.hops + 1,
                    ))

        # If same-family filter yielded nothing, fall back to same-group (distance <= 0.3)
        if not candidates:
            source_family = current.get("role_family", "other")
            source_group = _FAMILY_GROUPS.get(source_family, "other")
            for cid, cnode in nodes.items():
                if cid == node_id:
                    continue
                # All zones are valid candidates now
                if _cross_family_distance(source_family, cnode.get("role_family", "other")) >= 1.0:
                    continue
                if cid not in best_cost:
                    continue
                target_family = cnode.get("role_family", "other")
                target_group = _FAMILY_GROUPS.get(target_family, "other")
                # Zero-overlap filter for same-family or same-group
                if source_family == target_family or source_group == target_group:
                    src_sk = set(s.lower() for s in current.get("must_skills", []))
                    tgt_sk = set(s.lower() for s in cnode.get("must_skills", []))
                    if src_sk and tgt_sk and not (src_sk & tgt_sk):
                        if not self._graph.has_edge(node_id, cid):
                            continue
                gap = _compute_gap_skills(current, cnode, profile_skills=profile_skills)
                gap_hours = sum(s.estimated_hours for s in gap)
                candidates.append({
                    "target": cid,
                    "target_label": cnode.get("label", cid),
                    "target_zone": cnode.get("zone", "transition"),
                    "path": [cid],
                    "gap_skills": [{"name": g.name, "estimated_hours": g.estimated_hours} for g in gap],
                    "total_hours": gap_hours if gap_hours > 0 else 40,
                    "safety_gain": round(_safety_score(cnode) - current_safety, 3),
                    "salary_p50": cnode.get("salary_p50") or 0,
                    "total_cost": best_cost[cid],
                    "tag": "",
                })

        if not candidates:
            return []

        # Sort candidates by composite score: prefer same-family, fewer gaps, better safety
        source_family = current.get("role_family", "other")
        source_group = _FAMILY_GROUPS.get(source_family, "other")
        def _route_score(r: dict) -> float:
            target_node = nodes.get(r["target"], {})
            target_family = target_node.get("role_family", "other")
            target_group = _FAMILY_GROUPS.get(target_family, "other")
            if target_family == source_family:
                family_bonus = 0.3
            elif target_group == source_group:
                family_bonus = 0.0  # same group, different family — neutral
            else:
                family_bonus = -0.2  # cross-group — penalize
            gap_penalty = len(r["gap_skills"]) * 0.05
            zone = r["target_zone"]
            zone_bonus = {"safe": 0.2, "leverage": 0.15, "transition": 0.05, "danger": -0.1}.get(zone, 0)
            return family_bonus + zone_bonus - gap_penalty + r["safety_gain"] * 0.01

        candidates.sort(key=lambda r: -_route_score(r))

        # Three-dimension route selection: cheapest / highest safety / highest salary
        by_cost = sorted(candidates, key=lambda r: r["total_cost"])
        by_safety = sorted(candidates, key=lambda r: -r["safety_gain"])
        by_salary = sorted(candidates, key=lambda r: -r["salary_p50"])

        result: list[dict[str, Any]] = []
        seen: set[str] = set()

        for route, tag in [
            (by_cost[0], "最快"),
            (by_safety[0], "最稳"),
            (by_salary[0], "高薪"),
        ]:
            if route["target"] not in seen:
                route["tag"] = tag
                result.append(route)
                seen.add(route["target"])

        # Zone diversity: if all results share the same zone, swap the last
        # slot for a candidate from a different zone (prefer transition > leverage)
        result_zones = {r["target_zone"] for r in result}
        if len(result_zones) == 1 and len(result) >= 2:
            for cand in sorted(candidates, key=lambda r: r["total_cost"]):
                if cand["target"] not in seen and cand["target_zone"] not in result_zones:
                    cand["tag"] = "挑战"
                    result[-1] = cand
                    seen.discard(result[-1]["target"])
                    seen.add(cand["target"])
                    break

        # Fill remaining slots
        for route in by_cost:
            if len(result) >= top_k:
                break
            if route["target"] not in seen:
                route["tag"] = "备选"
                result.append(route)
                seen.add(route["target"])

        return result[:top_k]

    # ------------------------------------------------------------------
    # Terrain score (read from DB — migrated from terrain_scorer.py)
    # ------------------------------------------------------------------

    def get_terrain_score(self, node_id: str, db_session: Session) -> dict[str, Any]:
        """Read terrain scores from DB job_scores table.

        Falls back to graph node JSON fields if no DB record exists.
        """
        try:
            from backend.models import JobScore
            score = db_session.query(JobScore).filter_by(node_id=node_id).first()
            if score is not None:
                return {
                    "node_id": node_id,
                    "replacement_pressure": score.replacement_pressure,
                    "human_ai_leverage": score.human_ai_leverage,
                    "zone": score.zone,
                    "data_quality": score.data_quality,
                    "runway_months": score.runway_months,
                    "pressure_breakdown": score.pressure_breakdown,
                    "leverage_breakdown": score.leverage_breakdown,
                    "coverage_ratio": score.coverage_ratio,
                    "theoretical_pressure": score.theoretical_pressure,
                    "trai_ratio": score.trai_ratio,
                    "cai_ratio": score.cai_ratio,
                }
        except Exception:
            pass

        # Fallback to graph node JSON fields
        node = self._nodes.get(node_id, {})
        return {
            "node_id": node_id,
            "replacement_pressure": node.get("ai_exposure", 50.0),
            "human_ai_leverage": node.get("human_premium", 50.0),
            "zone": node.get("zone", "transition"),
            "data_quality": node.get("data_quality", "low"),
            "runway_months": None,
            "pressure_breakdown": node.get("ai_exposure_breakdown", {}),
            "leverage_breakdown": node.get("human_premium_breakdown", {}),
            "coverage_ratio": None,
            "theoretical_pressure": None,
            "trai_ratio": None,
            "cai_ratio": None,
        }

# ── Shared singleton accessor ───────────────────────────────────────────────

_instance: GraphService | None = None


def get_graph_service(db: Session | None = None) -> GraphService:
    """Return the shared GraphService singleton, loading on first call."""
    global _instance
    if _instance is None:
        _instance = GraphService()
    _instance.load(db_session=db)  # no-op if already loaded
    return _instance
