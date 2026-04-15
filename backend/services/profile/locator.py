# -*- coding: utf-8 -*-
"""Graph locator — IDF-weighted positioning on career graph."""
from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any

from backend.services.profile.shared import FAMILY_KEYWORDS, _soft_skills_as_list


def _collect_profile_text(profile: dict[str, Any]) -> list[tuple[str, float]]:
    """Collect resume text fields with signal weights.

    Returns [(text, weight), ...] — stronger signals get higher weight.
    """
    texts: list[tuple[str, float]] = []
    # current_title (strongest signal)
    title = profile.get("current_title", "")
    if title and title.strip():
        texts.append((title, 3.0))
    # internships
    for intern in profile.get("internships", []):
        if isinstance(intern, dict):
            role = intern.get("role", "")
            desc = intern.get("description", "")
            if role:
                texts.append((role, 2.0))
            if desc:
                texts.append((desc, 1.5))
    # work experience
    for work in profile.get("work_experiences", []):
        if isinstance(work, dict):
            role = work.get("role", "")
            desc = work.get("description", "")
            if role:
                texts.append((role, 2.0))
            if desc:
                texts.append((desc, 1.5))
    # Also support 'experience' key (from sample_profile)
    for work in profile.get("experience", []):
        if isinstance(work, dict):
            title_val = work.get("title", "")
            desc = work.get("description", "")
            if title_val:
                texts.append((title_val, 2.0))
            if desc:
                texts.append((desc, 1.5))
    # projects
    for proj in profile.get("projects", []):
        if isinstance(proj, dict):
            name = proj.get("name", "")
            desc = proj.get("description", "")
            if name:
                texts.append((name, 1.5))
            if desc:
                texts.append((desc, 1.5))
    # knowledge areas
    for ka in profile.get("knowledge_areas", []):
        if ka and ka.strip():
            texts.append((ka, 1.0))
    # Also support 'knowledge' key
    for ka in profile.get("knowledge", []):
        if ka and ka.strip():
            texts.append((ka, 1.0))
    # certificates
    for cert in profile.get("certificates", []):
        cert_name = cert.get("name", "") if isinstance(cert, dict) else str(cert)
        if cert_name and cert_name.strip():
            texts.append((cert_name, 0.5))
    return texts


def _build_family_task_vocab(
    graph_nodes: dict[str, Any],
) -> dict[str, set[str]]:
    """Build family task vocabulary from graph node core_tasks.

    Only keeps phrases with length >= 3 to avoid false matches.
    """
    vocab: dict[str, set[str]] = defaultdict(set)
    for node in graph_nodes.values():
        fam = node.get("role_family", "")
        if not fam:
            continue
        for task in node.get("core_tasks", []):
            task = task.strip()
            if len(task) >= 3:
                vocab[fam].add(task)
    return dict(vocab)


def _infer_family_prior(
    profile: dict[str, Any],
    family_keywords: dict[str, list[str]],
    family_task_vocab: dict[str, set[str]],
) -> dict[str, float]:
    """Infer family prior distribution from resume text.

    Scans family_keywords and family_task_vocab, accumulates by signal weight,
    normalizes to [0, 1].
    """
    texts = _collect_profile_text(profile)
    if not texts:
        return {}

    family_score: dict[str, float] = defaultdict(float)

    for text, weight in texts:
        text_lower = text.lower()
        # keyword matching
        for fam, keywords in family_keywords.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    family_score[fam] += weight
        # core_tasks matching (stronger signal)
        for fam, tasks in family_task_vocab.items():
            for task in tasks:
                if task in text:
                    family_score[fam] += weight * 1.5

    if not family_score:
        return {}

    max_score = max(family_score.values())
    if max_score <= 0:
        return {}
    return {fam: score / max_score for fam, score in family_score.items()}


def _task_match(profile: dict[str, Any], node: dict[str, Any]) -> float:
    """Substring match of user project/internship descriptions against node core_tasks."""
    core_tasks = [
        t.strip() for t in node.get("core_tasks", []) if t and len(t.strip()) >= 3
    ]
    if not core_tasks:
        return 0.0

    user_text_parts: list[str] = []
    for proj in profile.get("projects", []):
        if isinstance(proj, dict):
            user_text_parts.append(proj.get("name", ""))
            user_text_parts.append(proj.get("description", ""))
    for intern in profile.get("internships", []):
        if isinstance(intern, dict):
            user_text_parts.append(intern.get("role", ""))
            user_text_parts.append(intern.get("description", ""))
    for work in profile.get("work_experiences", []):
        if isinstance(work, dict):
            user_text_parts.append(work.get("description", ""))
    # Also support 'experience' key
    for work in profile.get("experience", []):
        if isinstance(work, dict):
            user_text_parts.append(work.get("description", ""))
    user_text = " ".join(user_text_parts).strip()
    if not user_text:
        return 0.0

    hits = sum(1 for task in core_tasks if task in user_text)
    return hits / len(core_tasks)


def _skill_names_from_profile(
    profile: dict[str, Any],
    graph_skill_vocab: set[str] | None = None,
) -> set[str]:
    """Extract skill name set from user profile (lowercased for matching).

    Includes ESCO canonical name, raw_name, knowledge_areas, and
    scans project/internship descriptions for graph skill vocab matches.
    """
    names: set[str] = set()
    for s in profile.get("skills", []):
        if isinstance(s, dict):
            name = s.get("name", "")
            if name.strip():
                names.add(name.strip().lower())
            raw = s.get("raw_name", "")
            if raw.strip():
                names.add(raw.strip().lower())
        else:
            name = str(s)
            if name.strip():
                names.add(name.strip().lower())
    # knowledge_areas as weak skill signals
    for ka in profile.get("knowledge_areas", []):
        if ka and ka.strip():
            names.add(ka.strip().lower())
    # Also support 'knowledge' key
    for ka in profile.get("knowledge", []):
        if ka and ka.strip():
            names.add(ka.strip().lower())
    # Scan descriptions for graph skill vocab matches
    if graph_skill_vocab:
        desc_texts: list[str] = []
        for proj in profile.get("projects", []):
            if isinstance(proj, dict):
                desc_texts.append(proj.get("name", ""))
                desc_texts.append(proj.get("description", ""))
                for su in proj.get("skills_used", []):
                    if su and su.strip():
                        names.add(su.strip().lower())
                # Also support 'tech_stack' key
                for su in proj.get("tech_stack", []):
                    if su and su.strip():
                        names.add(su.strip().lower())
        for intern in profile.get("internships", []):
            if isinstance(intern, dict):
                desc_texts.append(intern.get("role", ""))
                desc_texts.append(intern.get("description", ""))
        for work in profile.get("work_experiences", []):
            if isinstance(work, dict):
                desc_texts.append(work.get("description", ""))
        for work in profile.get("experience", []):
            if isinstance(work, dict):
                desc_texts.append(work.get("description", ""))
        combined = " ".join(desc_texts).lower()
        if combined.strip():
            for skill in graph_skill_vocab:
                if len(skill) >= 2 and skill in combined:
                    names.add(skill)
    return names


def _node_skill_set(node: dict[str, Any]) -> set[str]:
    """Extract must_skills set from graph node (lowercased)."""
    return {s.strip().lower() for s in node.get("must_skills", []) if s and s.strip()}


def _build_skill_idf(graph_nodes: dict[str, Any]) -> dict[str, float]:
    """Compute IDF weight for each skill across all graph nodes.

    IDF = log((N+1) / (1 + doc_count))
    """
    skill_doc_count: dict[str, int] = {}
    total = len(graph_nodes)
    for node in graph_nodes.values():
        seen: set[str] = set()
        for s in node.get("must_skills", []):
            sl = s.strip().lower()
            if sl and sl not in seen:
                skill_doc_count[sl] = skill_doc_count.get(sl, 0) + 1
                seen.add(sl)
    return {
        skill: math.log((total + 1) / (1 + cnt))
        for skill, cnt in skill_doc_count.items()
    }


def _weighted_skill_match(
    user_skills: set[str],
    node_skills: set[str],
    idf: dict[str, float],
) -> float:
    """IDF-weighted skill match score.

    Numerator: sum of IDF for skills in both user and node.
    Denominator: sum of IDF for all node must_skills.
    Result range [0, 1].
    """
    if not node_skills:
        return 0.0
    total_w = sum(idf.get(s, 1.0) for s in node_skills)
    if total_w == 0:
        return 0.0
    match_w = sum(idf.get(s, 1.0) for s in (user_skills & node_skills))
    return match_w / total_w


def _extract_terms(text: str) -> set[str]:
    """Extract matching terms from mixed Chinese/English text.

    English: split by separators; Chinese: contiguous sequences + bigrams.
    """
    parts: set[str] = set()
    for token in text.replace("/", " ").replace("-", " ").replace("_", " ").split():
        if token:
            parts.add(token)
    for match in re.finditer(r"[\u4e00-\u9fff]{2,}", text):
        seq = match.group()
        parts.add(seq)
        for i in range(len(seq) - 1):
            parts.add(seq[i: i + 2])
    return parts


def _title_bonus(user_title: str, node_label: str) -> float:
    """Title match score, returns 0-1.

    1.0 = full substring hit
    0.5 = partial term overlap (including Chinese bigrams)
    0.0 = unrelated
    """
    if not user_title or not node_label:
        return 0.0
    ut = user_title.strip().lower()
    nl = node_label.strip().lower()
    if ut in nl or nl in ut:
        return 1.0
    ut_terms = _extract_terms(ut)
    nl_terms = _extract_terms(nl)
    if not ut_terms or not nl_terms:
        return 0.0
    overlap = ut_terms & nl_terms
    if overlap and len(overlap) >= max(1, min(len(ut_terms), len(nl_terms)) // 2):
        return 0.5
    return 0.0


def _soft_match_lite(required: str, user_comps: set[str]) -> bool:
    """Lightweight competency matching for positioning stage.

    - Exact match → True
    - Short word (<=2 chars) only matches as prefix
    - Long words: bigram Jaccard >= 0.2
    """
    req = required.strip()
    if not req:
        return False
    for comp in user_comps:
        comp = comp.strip()
        if not comp:
            continue
        if req == comp:
            return True
        shorter, longer = (req, comp) if len(req) <= len(comp) else (comp, req)
        if len(shorter) <= 2:
            if longer.startswith(shorter):
                return True
            continue
        req_bg = (
            {req[i: i + 2] for i in range(len(req) - 1)} if len(req) >= 2 else {req}
        )
        comp_bg = (
            {comp[i: i + 2] for i in range(len(comp) - 1)}
            if len(comp) >= 2
            else {comp}
        )
        union = req_bg | comp_bg
        if union and len(req_bg & comp_bg) / len(union) >= 0.2:
            return True
    return False


def _competency_match(profile: dict[str, Any], node: dict[str, Any]) -> float:
    """Match user competencies against node soft_skills, returns 0-1."""
    node_soft = {s for s in _soft_skills_as_list(node.get("soft_skills", []))}
    if not node_soft:
        return 0.0
    user_comp_names: set[str] = set()
    # Support 'competencies' list
    for c in profile.get("competencies", []):
        name = c.get("name", "") if isinstance(c, dict) else str(c)
        if name.strip():
            user_comp_names.add(name.strip())
    # Support 'competency' dict (from sample_profile)
    comp_dict = profile.get("competency", {})
    if isinstance(comp_dict, dict):
        for name in comp_dict:
            if name.strip():
                user_comp_names.add(name.strip())
    # Support 'soft_skills' dict
    ss_dict = profile.get("soft_skills", {})
    if isinstance(ss_dict, dict):
        for name in ss_dict:
            if name.strip():
                user_comp_names.add(name.strip())
    if not user_comp_names:
        return 0.0
    hit = sum(1 for s in node_soft if _soft_match_lite(s, user_comp_names))
    return hit / len(node_soft)


def locate_on_graph(
    profile: dict,
    graph_service: Any,
    nodes: list[dict] | None = None,
) -> dict:
    """IDF-weighted positioning on career graph.

    Two-stage scoring:
      Stage 1 — Infer family prior from resume text
      Stage 2 — Multi-factor scoring + family prior multiplicative boost

    Returns:
        {node_id, label, score, family_confidence, candidates: top-5}
    """
    graph_nodes = graph_service._nodes
    user_title = profile.get("current_title", "")
    has_title = bool(user_title and user_title.strip())

    idf = _build_skill_idf(graph_nodes)

    # Build global skill vocab for description scanning
    graph_skill_vocab: set[str] = set()
    for node in graph_nodes.values():
        for s in node.get("must_skills", []):
            if s and s.strip() and len(s.strip()) >= 2:
                graph_skill_vocab.add(s.strip().lower())

    user_skills = _skill_names_from_profile(profile, graph_skill_vocab)

    # Stage 1: Family prior
    family_task_vocab = _build_family_task_vocab(graph_nodes)
    family_prior = _infer_family_prior(profile, FAMILY_KEYWORDS, family_task_vocab)

    # Build candidate nodes list
    if nodes is not None:
        candidate_nodes = {
            n.get("node_id", ""): n for n in nodes if not n.get("is_milestone", False)
        }
    else:
        candidate_nodes = {
            nid: n for nid, n in graph_nodes.items() if not n.get("is_milestone", False)
        }

    # Stage 2: Multi-factor scoring
    scores: list[tuple[str, float]] = []

    for nid, node in candidate_nodes.items():
        node_skills = _node_skill_set(node)
        skill_score = _weighted_skill_match(user_skills, node_skills, idf)
        title_score = _title_bonus(user_title, node.get("label", ""))
        comp_score = _competency_match(profile, node)
        task_score = _task_match(profile, node)

        # Weight blend: with-title vs student/no-title
        if has_title:
            base = (
                skill_score * 0.45
                + task_score * 0.10
                + title_score * 0.25
                + comp_score * 0.20
            )
        else:
            base = skill_score * 0.55 + task_score * 0.20 + comp_score * 0.25

        # Family prior multiplicative boost (max +35%)
        node_family = node.get("role_family", "")
        family_conf = family_prior.get(node_family, 0.0)
        combined = base * (1.0 + 0.35 * family_conf)

        scores.append((nid, combined))

    scores.sort(key=lambda x: -x[1])

    if not scores:
        return {
            "node_id": None,
            "label": "",
            "score": 0.0,
            "family_confidence": 0.0,
            "candidates": [],
        }

    best_id, best_score = scores[0]
    best_node = candidate_nodes.get(best_id, {})
    best_family = best_node.get("role_family", "")
    best_family_conf = family_prior.get(best_family, 0.0)

    candidates = [
        {
            "node_id": nid,
            "label": candidate_nodes.get(nid, {}).get("label", nid),
            "score": round(s, 4),
        }
        for nid, s in scores[:5]
    ]

    return {
        "node_id": best_id,
        "label": best_node.get("label", best_id),
        "score": round(best_score, 4),
        "family_confidence": round(best_family_conf, 4),
        "candidates": candidates,
    }
