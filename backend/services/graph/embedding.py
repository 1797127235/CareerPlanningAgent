"""Node embedding pre-filter for graph matching."""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path

from backend.config import DASHSCOPE_API_KEY, LLM_BASE_URL
from backend.services.graph.query import _get_graph_nodes
from backend.services.graph.skills import _expand_chinese_tokens

logger = logging.getLogger(__name__)

_NODE_EMBEDDINGS: dict | None = None
_NODE_EMBEDDINGS_MTIME: float = 0.0


def _load_node_embeddings() -> dict:
    global _NODE_EMBEDDINGS, _NODE_EMBEDDINGS_MTIME
    path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "node_embeddings.json"
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0.0
    if _NODE_EMBEDDINGS is not None and mtime == _NODE_EMBEDDINGS_MTIME:
        return _NODE_EMBEDDINGS
    try:
        with open(path, "r", encoding="utf-8") as f:
            _NODE_EMBEDDINGS = json.load(f)
        _NODE_EMBEDDINGS_MTIME = mtime
    except Exception:
        _NODE_EMBEDDINGS = {"nodes": {}}
        _NODE_EMBEDDINGS_MTIME = 0.0
    return _NODE_EMBEDDINGS


def embedding_prefilter(
    profile_data: dict,
    *,
    pin_node_ids: list[str] | None = None,
    min_k: int = 12,
    max_k: int = 18,
    ratio: float = 0.65,
) -> list[str]:
    """Use cosine similarity to narrow candidate nodes before LLM matching.

    Args:
        profile_data: User profile dict (skills, projects, job_target, …).
        pin_node_ids: Node IDs that MUST appear in the result (e.g. job_target match).
        min_k / max_k: Floor / ceiling on how many candidates to return.
        ratio: Relative similarity threshold (keep nodes with sim >= top_sim * ratio).

    Returns sorted list of node_ids (best match first). Falls back to all nodes
    if embeddings are unavailable or the API call fails.
    """
    import numpy as np

    all_node_ids = list(_get_graph_nodes().keys())

    emb_data = _load_node_embeddings()
    node_embs = emb_data.get("nodes", {})
    if not node_embs:
        return all_node_ids

    skills = [s.get("name", "") for s in profile_data.get("skills", []) if isinstance(s, dict) and s.get("name")]
    if not skills:
        return all_node_ids

    parts = [" ".join(skills)]
    jt = profile_data.get("job_target") or ""
    if jt:
        parts.append(jt)
    for p in profile_data.get("projects", [])[:3]:
        if not isinstance(p, dict):
            continue
        pname = p.get("name", "")
        tech = p.get("tech_stack", "") or p.get("technologies", "")
        desc = p.get("description", "") or p.get("highlights", "")
        if pname:
            line = pname
            if tech:
                line += f"({str(tech)[:60]})"
            if desc:
                line += f": {str(desc)[:80]}"
            parts.append(line)

    user_text = " | ".join(parts)

    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=LLM_BASE_URL,
            timeout=15,
        )
        resp = client.embeddings.create(
            model=emb_data.get("embedding_model", "text-embedding-v4"),
            input=[user_text],
        )
        user_vec = np.array(resp.data[0].embedding)
    except Exception as e:
        logger.warning("Embedding pre-filter failed, falling back to all nodes: %s", e)
        return all_node_ids

    node_ids = list(node_embs.keys())
    node_vecs = np.array([node_embs[nid] for nid in node_ids])
    norms = np.linalg.norm(node_vecs, axis=1, keepdims=True)
    node_vecs_normed = node_vecs / norms
    user_normed = user_vec / np.linalg.norm(user_vec)

    sims = node_vecs_normed @ user_normed
    ranking = np.argsort(sims)[::-1]

    top_sim = sims[ranking[0]]
    threshold = top_sim * ratio
    candidates = [node_ids[i] for i in ranking if sims[i] >= threshold]

    if len(candidates) < min_k:
        candidates = [node_ids[i] for i in ranking[:min_k]]
    elif len(candidates) > max_k:
        candidates = candidates[:max_k]

    if pin_node_ids:
        for nid in pin_node_ids:
            if nid in all_node_ids and nid not in candidates:
                candidates.append(nid)

    # ── Core-tasks text-match layer (work-content driven, not skill-name driven) ──
    # Some resumes have rich project/internship descriptions that clearly signal
    # a direction (e.g. "测试用例/缺陷/功能测试" for QA) but their generic
    # skill list (Python/SQL) causes embedding similarity to drown the signal.
    # We scan user text against each node's core_tasks and force-match nodes
    # with >= 2 task hits into the candidate pool so the LLM sees them.
    from backend.services._shared.text_extract import build_user_text
    user_text_combined = build_user_text(profile_data)

    graph_nodes = _get_graph_nodes()
    task_forced: list[str] = []
    for nid, node in graph_nodes.items():
        core_tasks = [t.strip() for t in node.get("core_tasks", []) if t and len(t.strip()) >= 3]
        if not core_tasks:
            continue
        # Use expanded tokens (Chinese prefixes etc.) for robust matching
        expanded = _expand_chinese_tokens(core_tasks)
        hits = sum(1 for token in expanded if len(token) >= 2 and token in user_text_combined)
        # Threshold: >=2 distinct task-token hits, or strong proportional match
        if hits >= 2 or (len(core_tasks) >= 3 and hits / len(core_tasks) >= 0.3):
            task_forced.append(nid)

    forced_count = 0
    for nid in task_forced:
        if nid not in candidates:
            candidates.append(nid)
            forced_count += 1
    if forced_count:
        logger.info("Task-match layer forced %d nodes into prefilter candidates", forced_count)

    logger.info("Embedding prefilter: %d/%d nodes selected", len(candidates), len(all_node_ids))
    return candidates
