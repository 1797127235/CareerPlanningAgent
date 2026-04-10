# -*- coding: utf-8 -*-
"""
GraphService — unified graph access layer.

Replaces the scattered graph_loader, escape_router, terrain_scorer (read portion),
and transition_probability modules with a single Service class.

Public methods:
  load()                — Load graph.json, build NetworkX DiGraph, cache singleton
  get_node()            — Get node by node_id
  get_node_by_label()   — Get node by Chinese label
  search_nodes()        — Search nodes by keyword
  shortest_path()       — Dijkstra shortest path
  bfs_reachable()       — BFS reachable within max_hops
  find_escape_routes()  — Weighted Dijkstra escape route calculation
  get_terrain_score()   — Read terrain scores from DB
  compute_transition_probability() — Stub (deferred to later task)
"""
from __future__ import annotations

import heapq
import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

import networkx as nx
from sqlalchemy.orm import Session

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_GRAPH_PATH = _PROJECT_ROOT / "data" / "graph.json"

_DIFF_WEIGHT = {"低": 1.0, "中": 2.0, "高": 3.0}


# ── Skill embedding cache for semantic matching ───────────────────────────────

_SKILL_EMB_PATH = _PROJECT_ROOT / "data" / "skill_embeddings.json"


class _SkillEmbedder:
    """Skill embedding cache with file persistence.

    Graph skill embeddings are pre-computed and cached to file.
    User skill embeddings are computed on-the-fly and cached in memory.
    """

    def __init__(self):
        self._cache: dict[str, list[float]] = {}
        self._client = None
        self._loaded = False

    def _get_client(self):
        if self._client is None:
            import os
            from openai import OpenAI
            api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
            if not api_key or api_key == "sk-placeholder":
                return None
            base_url = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            self._client = OpenAI(base_url=base_url, api_key=api_key, timeout=10, max_retries=1)
        return self._client

    def load_cache(self):
        """Load pre-computed embeddings from file."""
        if self._loaded:
            return
        self._loaded = True
        if _SKILL_EMB_PATH.exists():
            try:
                data = json.loads(_SKILL_EMB_PATH.read_text(encoding="utf-8"))
                self._cache.update(data)
                logger.info("Loaded %d skill embeddings from cache", len(data))
            except Exception as e:
                logger.warning("Failed to load skill embeddings: %s", e)

    def save_cache(self):
        """Save current cache to file."""
        try:
            _SKILL_EMB_PATH.write_text(
                json.dumps(self._cache, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as e:
            logger.warning("Failed to save skill embeddings: %s", e)

    def _embed_batch(self, texts: list[str]) -> dict[str, list[float]]:
        """Embed a batch of texts (max 10 per DashScope call)."""
        client = self._get_client()
        if not client:
            return {}
        result = {}
        # DashScope limit: 10 per batch
        for i in range(0, len(texts), 10):
            batch = texts[i:i + 10]
            try:
                resp = client.embeddings.create(model="text-embedding-v3", input=batch)
                for text, emb in zip(batch, resp.data):
                    result[text] = emb.embedding
                    self._cache[text] = emb.embedding
            except Exception as e:
                logger.warning("Batch embedding failed: %s", e)
        return result

    def ensure_embedded(self, skills: list[str]) -> None:
        """Ensure all skills have embeddings (batch embed missing ones)."""
        missing = [s for s in skills if s not in self._cache]
        if missing:
            self._embed_batch(missing)

    def best_similarity(self, skill: str, candidates: list[str]) -> float:
        """Find the highest cosine similarity between skill and any candidate."""
        skill_vec = self._cache.get(skill)
        if skill_vec is None:
            return 0.0
        best = 0.0
        for c in candidates:
            c_vec = self._cache.get(c)
            if c_vec is None:
                continue
            dot = sum(a * b for a, b in zip(skill_vec, c_vec))
            norm_a = math.sqrt(sum(a * a for a in skill_vec))
            norm_b = math.sqrt(sum(b * b for b in c_vec))
            if norm_a > 0 and norm_b > 0:
                sim = dot / (norm_a * norm_b)
                if sim > best:
                    best = sim
        return best


_skill_embedder: _SkillEmbedder | None = None


def _get_skill_embedder() -> _SkillEmbedder | None:
    """Get or create the singleton skill embedder."""
    global _skill_embedder
    if _skill_embedder is None:
        _skill_embedder = _SkillEmbedder()
        _skill_embedder.load_cache()
    if _skill_embedder._get_client() is None:
        return None
    return _skill_embedder


def find_skill_for_topic(topic_title: str, all_graph_skills: list[str], threshold: float = 0.65) -> str | None:
    """Find the best matching graph skill for a learning topic title.

    Uses two-tier matching:
    1. Fast: string containment check (no API call)
    2. Semantic: embedding cosine similarity if no string match

    Returns the best matching skill name, or None.
    """
    if not topic_title or not all_graph_skills:
        return None

    title_lower = topic_title.lower()

    # Tier 1: fast string containment (no API call, no latency)
    for skill in all_graph_skills:
        if skill.lower() in title_lower or title_lower in skill.lower():
            return skill

    # Tier 2: semantic similarity (uses cached embeddings)
    try:
        embedder = _get_skill_embedder()
        if embedder is None:
            return None

        embedder.ensure_embedded(all_graph_skills)
        embedder.ensure_embedded([topic_title])

        best_skill = None
        best_sim = threshold  # minimum threshold

        # best_similarity(skill, [topic_title]) = similarity between skill and topic
        for skill in all_graph_skills:
            sim = embedder.best_similarity(skill, [topic_title])
            if sim > best_sim:
                best_sim = sim
                best_skill = skill

        if best_skill:
            embedder.save_cache()

        return best_skill
    except Exception as e:
        logger.debug("Semantic skill matching failed for topic '%s': %s", topic_title, e)
        return None


# ── Family group mapping (from escape_router.py) ──────────────────────────
_FAMILY_GROUPS: dict[str, str] = {
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
}


# ── Direction modifier matrix (asymmetric transition costs) ───────────────
# Calibrated from: Cortes & Gallipoli (2018), Alabdulkareem et al. (2018),
# Schubert et al. (2024), Neffke et al. (2024)
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
    current_node: dict,
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


# ═══════════════════════════════════════════════════════════════════════════
# GraphService
# ═══════════════════════════════════════════════════════════════════════════

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
            from backend.db_models import JobScore
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

    def _get_edges(self) -> list[tuple[str, str]]:
        """Return list of (source, target) pairs — for test helpers."""
        if self._graph is None:
            return []
        return list(self._graph.edges())

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

    def get_node_by_label(self, label: str) -> dict | None:
        """Get a node by its Chinese label."""
        node_id = self._label_index.get(label)
        if node_id is None:
            return None
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
        effective_len = sum(2 if "\u4e00" <= c <= "\u9fff" else 1 for c in kw)

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

    def recommend_by_skills(self, user_skills: list[str], top_n: int = 5, preferences: dict | None = None) -> list[dict]:
        """Recommend jobs by matching user skills + career preferences.

        Scoring: skill_match * 0.6 + preference_match * 0.4
        Skill matching: exact (1.0) + semantic (0.7) per skill
        Preference matching: based on role_family, zone, career_level, replacement_pressure

        Returns top_n nodes sorted by total score (descending).
        """
        if self._graph is None:
            self.load()
        if not user_skills:
            return []

        user_set = {s.lower().strip() for s in user_skills if s}
        user_list = [s.strip() for s in user_skills if s.strip()]

        # Try to get embeddings for semantic matching
        embedder = _get_skill_embedder()

        # Batch-embed all skills upfront (graph skills from cache, user skills on-the-fly)
        if embedder:
            all_graph_skills = set()
            for node in self._nodes.values():
                all_graph_skills.update(s.lower().strip() for s in node.get("must_skills", []))
            embedder.ensure_embedded(list(all_graph_skills))
            embedder.ensure_embedded(user_list)
            embedder.save_cache()  # Persist for next time

        scored: list[tuple[float, dict]] = []

        for node in self._nodes.values():
            must = {s.lower().strip() for s in node.get("must_skills", [])}
            if not must:
                continue

            # Tier 1: exact match
            exact_overlap = user_set & must
            exact_missing = must - user_set

            # Tier 2: semantic match for remaining skills
            semantic_matches: list[str] = []
            final_missing = set(exact_missing)

            if embedder and exact_missing and user_list:
                for missing_skill in list(exact_missing):
                    best_sim = embedder.best_similarity(missing_skill, user_list)
                    if best_sim >= 0.70:  # Threshold for semantic match
                        semantic_matches.append(missing_skill)
                        final_missing.discard(missing_skill)

            skill_score = len(exact_overlap) + len(semantic_matches) * 0.7

            # Preference scoring (0.0 - 1.0)
            pref_score = 0.0
            if preferences and skill_score > 0:
                pref_hits = 0
                pref_total = 0

                # Work style → role_family mapping
                ws = preferences.get("work_style", "")
                if ws:
                    pref_total += 1
                    family = node.get("role_family", "").lower()
                    ws_map = {
                        "tech": ["后端", "前端", "全栈", "系统", "移动", "游戏", "区块链"],
                        "product": ["产品", "设计", "社区", "文档"],
                        "data": ["数据", "ai", "ml"],
                        "management": ["管理", "架构"],
                    }
                    if any(kw in family for kw in ws_map.get(ws, [])):
                        pref_hits += 1

                # AI attitude → replacement_pressure
                ai_att = preferences.get("ai_attitude", "")
                if ai_att:
                    pref_total += 1
                    rp = node.get("replacement_pressure", 50)
                    if ai_att == "do_ai" and "ai" in node.get("role_family", "").lower():
                        pref_hits += 1
                    elif ai_att == "avoid_ai" and rp < 30:
                        pref_hits += 1
                    elif ai_att == "no_preference":
                        pref_hits += 0.5

                # Value priority → zone
                vp = preferences.get("value_priority", "")
                if vp:
                    pref_total += 1
                    zone = node.get("zone", "")
                    if vp == "stability" and zone == "safe":
                        pref_hits += 1
                    elif vp == "growth" and zone == "thrive":
                        pref_hits += 1
                    elif vp == "innovation" and zone in ("thrive", "transition"):
                        pref_hits += 0.7
                    elif vp == "balance":
                        pref_hits += 0.5  # Neutral

                # Company type → career_level
                ct = preferences.get("company_type", "")
                if ct:
                    pref_total += 1
                    cl = node.get("career_level", 2)
                    if ct == "big_tech" and node.get("skill_count", 0) >= 6:
                        pref_hits += 1  # Big tech wants full-stack skills
                    elif ct == "startup" and cl <= 3:
                        pref_hits += 1  # Startups want ICs
                    elif ct == "state_owned" and node.get("zone") == "safe":
                        pref_hits += 1
                    elif ct == "growing":
                        pref_hits += 0.5

                pref_score = pref_hits / pref_total if pref_total > 0 else 0.0

            # Combined score: skill (60%) + preference (40%)
            total_score = skill_score * 0.6 + pref_score * skill_score * 0.4
            if total_score > 0:
                info = dict(node)
                info["overlap_count"] = len(exact_overlap) + len(semantic_matches)
                info["overlap_skills"] = sorted(exact_overlap)
                if semantic_matches:
                    info["semantic_matches"] = sorted(semantic_matches)
                info["missing_skills"] = sorted(final_missing)
                scored.append((total_score, info))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_n]]

    # ------------------------------------------------------------------
    # Shortest path (migrated from graph_loader.py)
    # ------------------------------------------------------------------

    def shortest_path(self, source: str, target: str) -> dict[str, Any] | None:
        """Dijkstra shortest path with difficulty-mapped weights (低=1, 中=2, 高=3)."""
        if self._graph is None:
            return None
        try:
            path_nodes = nx.dijkstra_path(self._graph, source, target, weight="weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

        edges = []
        total_weight = 0.0
        for i in range(len(path_nodes) - 1):
            edge_data = self._graph.get_edge_data(path_nodes[i], path_nodes[i + 1])
            if edge_data:
                edges.append(edge_data)
                total_weight += edge_data.get("weight", 2.0)

        return {
            "path_nodes": path_nodes,
            "path_edges": edges,
            "total_difficulty_score": total_weight,
        }

    # ------------------------------------------------------------------
    # BFS reachable (migrated from graph_loader.py)
    # ------------------------------------------------------------------

    def bfs_reachable(self, node_id: str, max_hops: int = 2) -> list[dict[str, Any]]:
        """BFS reachable nodes with path and cumulative cost."""
        if self._graph is None or node_id not in self._graph:
            return []

        visited = {node_id}
        queue: list[tuple[str, list[str], list[dict], float]] = [
            (node_id, [node_id], [], 0.0)
        ]
        results = []
        head = 0

        while head < len(queue):
            current, path, edges, cost = queue[head]
            head += 1

            for _, neighbor, edge_data in self._graph.out_edges(current, data=True):
                if neighbor in visited:
                    continue
                new_path = path + [neighbor]
                new_edges = edges + [edge_data]
                new_cost = cost + edge_data.get("weight", 2.0)

                if len(new_path) - 1 <= max_hops:
                    visited.add(neighbor)
                    target_node = self._nodes.get(neighbor, {})
                    results.append({
                        "target_node": {
                            "node_id": neighbor,
                            "label": target_node.get("label", neighbor),
                        },
                        "path_nodes": new_path,
                        "path_edges": new_edges,
                        "total_difficulty_score": new_cost,
                        "hops": len(new_path) - 1,
                    })
                    if len(new_path) - 1 < max_hops:
                        queue.append((neighbor, new_path, new_edges, new_cost))

        return results

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
                # Filter out cross-group career jumps (e.g. QA → management/architect)
                source_family = current.get("role_family", "other")
                target_family = node.get("role_family", "other")
                if _cross_family_distance(source_family, target_family) < 1.0:
                    # For same-family routes: skip if zero skill overlap (unrelated sub-field)
                    # Cross-family routes (e.g. tech→management) are exempt — skills differ by design
                    if source_family == target_family:
                        src_skills = set(s.lower() for s in current.get("must_skills", []))
                        tgt_skills = set(s.lower() for s in node.get("must_skills", []))
                        if src_skills and tgt_skills and not (src_skills & tgt_skills):
                            if not self._graph.has_edge(node_id, state.node_id):
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
                edge_c = _edge_cost(current, node, neighbor, edge)
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
            for cid, cnode in nodes.items():
                if cid == node_id:
                    continue
                # All zones are valid candidates now
                if _cross_family_distance(source_family, cnode.get("role_family", "other")) >= 1.0:
                    continue
                if cid not in best_cost:
                    continue
                # Same-family zero-overlap filter (cross-family exempt)
                if source_family == cnode.get("role_family", "other"):
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
        def _route_score(r: dict) -> float:
            target_node = nodes.get(r["target"], {})
            family_bonus = 0.3 if target_node.get("role_family") == source_family else 0.0
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
            from backend.db_models import JobScore
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

    # ------------------------------------------------------------------
    # Transition probability (stub — deferred to later task)
    # ------------------------------------------------------------------

    def compute_transition_probability(self, source: str, target: str) -> float:
        """Compute P(source -> target).

        TODO: Migrate full Sigmoid model from transition_probability.py.
        Currently returns a neutral 0.5 placeholder.
        """
        return 0.5


# ── Shared singleton accessor ───────────────────────────────────────────────

_instance: GraphService | None = None


def get_graph_service(db: Session | None = None) -> GraphService:
    """Return the shared GraphService singleton, loading on first call."""
    global _instance
    if _instance is None:
        _instance = GraphService()
    _instance.load(db_session=db)  # no-op if already loaded
    return _instance
