"""Automatic graph location for user profiles."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from backend.models import CareerGoal, Profile
from backend.services.graph.matching import _llm_match_role, find_role_id_for_job_target
from backend.services.graph.query import get_graph_nodes, get_graph_edges
from backend.services.graph.skills import (
    _build_work_content_summary,
    _extract_implied_skills_from_text,
    _expand_chinese_tokens,
)

logger = logging.getLogger(__name__)


def _auto_locate_on_graph(
    profile_id: int, user_id: int, profile_data: dict, db: Session
) -> dict | None:
    """Locate profile on career graph + generate recommendations in one LLM call.

    Returns current position dict and caches recommendations for instant loading.
    """
    logger.info(
        "[AUTO-LOCATE-START] profile_id=%d job_target=%r skills=%d",
        profile_id,
        profile_data.get("job_target", ""),
        len(profile_data.get("skills", [])),
    )
    profile = None
    p_hash = None
    rec_resp = None
    try:
        from backend.services.graph import get_graph_service

        graph = get_graph_service(db)

        llm_result = _llm_match_role(profile_data)
        if not llm_result:
            return None

        current_pos = llm_result.get("current_position", llm_result)
        node_id = current_pos["role_id"]

        node = graph.get_node(node_id)
        if not node:
            return None
        node_label = node.get("label", node_id)

        existing_goal = (
            db.query(CareerGoal)
            .filter_by(user_id=user_id, profile_id=profile_id, is_active=True)
            .first()
        )
        if existing_goal:
            db.query(CareerGoal).filter_by(
                user_id=user_id, profile_id=profile_id, is_active=True
            ).update({"from_node_id": node_id})
        else:
            goal = CareerGoal(
                user_id=user_id,
                profile_id=profile_id,
                from_node_id=node_id,
                target_node_id="",
                target_label="",
                target_zone="",
                is_primary=True,
            )
            db.add(goal)

        # Cache recommendations from the same LLM call
        recs_raw = llm_result.get("recommendations", [])
        enriched = []
        if recs_raw:
            from backend.routers.recommendations import _save_rec_cache
            from backend.services.gap_analyzer import profile_hash

            graph_nodes = get_graph_nodes()

            skills = [
                s.get("name", "")
                for s in profile_data.get("skills", [])
                if s.get("name")
            ]
            for r in recs_raw[:6]:
                rid = r.get("role_id", "")
                if rid not in graph_nodes:
                    logger.warning(
                        "LLM hallucinated role_id=%s in auto_locate, skipping", rid
                    )
                    continue
                gn = graph_nodes[rid]
                enriched.append(
                    {
                        "role_id": rid,
                        "label": r.get("label", gn.get("label", rid)),
                        "affinity_pct": r.get("affinity_pct", 50),
                        "matched_skills": [],
                        "gap_skills": gn.get("must_skills", [])[:4],
                        "gap_hours": 0,
                        "zone": gn.get("zone", "safe"),
                        "salary_p50": gn.get("salary_p50", 0),
                        "reason": r.get("reason", ""),
                        "channel": r.get("channel", "entry"),
                        "career_level": gn.get("career_level", 0),
                        "replacement_pressure": gn.get("replacement_pressure", 50),
                        "human_ai_leverage": gn.get("human_ai_leverage", 50),
                    }
                )

            # ── Locator only for backfill ranking, NOT override LLM ──
            # LLM now receives full project/internship text; its judgment is
            # more context-aware than skill-name-only IDF matching.
            from backend.services.profile.locator import locate_on_graph

            try:
                loc_result = locate_on_graph(profile_data, graph)
                loc_scores = {nid: s for nid, s in loc_result.get("all_scores", [])}
                # Store locator scores for backfill use, but keep LLM ranking
                for rec in enriched:
                    nid = rec["role_id"]
                    if nid in loc_scores:
                        rec["_loc_score"] = loc_scores[nid]
                logger.info(
                    "Locator scores computed for %d recommendations (not overriding LLM)",
                    len(enriched),
                )
            except Exception as e:
                logger.warning("Locator ranking failed: %s", e)

            # ── Seniority hard filter on LLM result ────────────────────
            # 应届生绝不推 L4+ 架构师/经理岗位，即便 LLM 推了也过滤掉
            exp_years = profile_data.get("experience_years", 0) or 0
            if exp_years == 0:
                enriched = [r for r in enriched if (r.get("career_level") or 0) <= 3]
            elif exp_years <= 1:
                enriched = [r for r in enriched if (r.get("career_level") or 0) <= 4]

            # ── Backfill: if LLM returns too few, supplement by skill+task overlap ──
            # Two-layer scoring:
            #   1) must_skills overlap (incl. text-scanned implied skills)
            #   2) core_tasks match against user project/internship text
            # A node with high task-match but low skill-overlap (e.g. QA where
            # user has generic Python/SQL but rich test descriptions) can still
            # rank high and be backfilled.
            user_skill_set = {
                (s.get("name") or "").lower().strip()
                for s in profile_data.get("skills", [])
                if isinstance(s, dict) and s.get("name")
            }
            user_skill_set |= _extract_implied_skills_from_text(profile_data)
            existing_ids = {r["role_id"] for r in enriched}

            # Build user text for task matching (same logic as prefilter)
            text_parts: list[str] = []
            rt = (profile_data.get("raw_text") or "").lower()
            if rt:
                text_parts.append(rt)
            for p in profile_data.get("projects", []):
                if isinstance(p, dict):
                    text_parts.append(str(p.get("name", "")).lower())
                    text_parts.append(
                        str(p.get("description", "") or p.get("highlights", "")).lower()
                    )
                elif isinstance(p, str):
                    text_parts.append(p.lower())
            for i in profile_data.get("internships", []):
                if isinstance(i, dict):
                    text_parts.append(str(i.get("role", "")).lower())
                    text_parts.append(
                        str(i.get("description", "") or i.get("highlights", "")).lower()
                    )
                elif isinstance(i, str):
                    text_parts.append(i.lower())
            user_text_combined = " ".join(text_parts)

            backfill_candidates = []
            for nid, node in graph_nodes.items():
                if nid in existing_ids:
                    continue
                cl = node.get("career_level", 0) or 0
                if exp_years == 0 and cl > 3:
                    continue
                if exp_years <= 1 and cl > 4:
                    continue
                # Expand node skills with Chinese prefix tokens for robust matching
                raw_skills = [
                    (s if isinstance(s, str) else s.get("name", "")).lower().strip()
                    for s in (node.get("must_skills") or [])
                ]
                expanded_skills = _expand_chinese_tokens(raw_skills)
                overlap = len(user_skill_set & expanded_skills)
                core_tasks = [
                    t.strip()
                    for t in node.get("core_tasks", [])
                    if t and len(t.strip()) >= 3
                ]
                expanded_tasks = _expand_chinese_tokens(core_tasks)
                task_hits = (
                    sum(
                        1
                        for t in expanded_tasks
                        if len(t) >= 2 and t in user_text_combined
                    )
                    if core_tasks
                    else 0
                )
                # Combined score: task hits weighted 2x, skill overlap 1x
                total_score = overlap + task_hits * 2
                if total_score == 0:
                    continue
                backfill_candidates.append((total_score, overlap, task_hits, nid, node))
            backfill_candidates.sort(key=lambda x: -x[0])

            backfilled = 0
            for total_score, overlap, task_hits, nid, node in backfill_candidates:
                if len(enriched) >= 6:
                    break
                # Higher base affinity when task-matches dominate
                base_affinity = min(60 + total_score * 5, 78)
                reason_parts = []
                if overlap:
                    reason_parts.append(f"技能画像与该方向有 {overlap} 项重合")
                if task_hits:
                    reason_parts.append(
                        f"项目/实习经历与该岗位核心任务有 {task_hits} 项匹配"
                    )
                enriched.append(
                    {
                        "role_id": nid,
                        "label": node.get("label", nid),
                        "affinity_pct": base_affinity,
                        "matched_skills": [],
                        "gap_skills": (node.get("must_skills") or [])[:4],
                        "gap_hours": 0,
                        "zone": node.get("zone", "safe"),
                        "salary_p50": node.get("salary_p50", 0),
                        "reason": "；".join(reason_parts)
                        or f"技能画像与该方向有 {overlap} 项重合",
                        "channel": "growth",
                        "career_level": node.get("career_level", 0),
                        "replacement_pressure": node.get("replacement_pressure", 50),
                        "human_ai_leverage": node.get("human_ai_leverage", 50),
                    }
                )
                backfilled += 1
            if backfilled:
                logger.info(
                    "Auto-locate backfill: added %d candidates (task+skill)", backfilled
                )

        # ── Fallback: if all LLM results were filtered, run skill-based backfill ──
        if not enriched:
            logger.info("All LLM recommendations filtered, running full backfill")
            user_skill_set = {
                (s.get("name") or "").lower().strip()
                for s in profile_data.get("skills", [])
                if isinstance(s, dict) and s.get("name")
            }
            user_skill_set |= _extract_implied_skills_from_text(profile_data)
            text_parts = []
            rt = (profile_data.get("raw_text") or "").lower()
            if rt:
                text_parts.append(rt)
            for p in profile_data.get("projects", []):
                if isinstance(p, dict):
                    text_parts.append(str(p.get("name", "")).lower())
                    text_parts.append(
                        str(p.get("description", "") or p.get("highlights", "")).lower()
                    )
                elif isinstance(p, str):
                    text_parts.append(p.lower())
            for i in profile_data.get("internships", []):
                if isinstance(i, dict):
                    text_parts.append(str(i.get("role", "")).lower())
                    text_parts.append(
                        str(i.get("description", "") or i.get("highlights", "")).lower()
                    )
                elif isinstance(i, str):
                    text_parts.append(i.lower())
            user_text_combined = " ".join(text_parts)
            exp_years = profile_data.get("experience_years", 0) or 0
            backfill_candidates = []
            for nid, node in graph_nodes.items():
                cl = node.get("career_level", 0) or 0
                if exp_years == 0 and cl > 3:
                    continue
                if exp_years <= 1 and cl > 4:
                    continue
                raw_skills = [
                    (s if isinstance(s, str) else s.get("name", "")).lower().strip()
                    for s in (node.get("must_skills") or [])
                ]
                expanded_skills = _expand_chinese_tokens(raw_skills)
                overlap = len(user_skill_set & expanded_skills)
                core_tasks = [
                    t.strip()
                    for t in node.get("core_tasks", [])
                    if t and len(t.strip()) >= 3
                ]
                expanded_tasks = _expand_chinese_tokens(core_tasks)
                task_hits = (
                    sum(
                        1
                        for t in expanded_tasks
                        if len(t) >= 2 and t in user_text_combined
                    )
                    if core_tasks
                    else 0
                )
                total_score = overlap + task_hits * 2
                if total_score == 0:
                    continue
                backfill_candidates.append((total_score, overlap, task_hits, nid, node))
            backfill_candidates.sort(key=lambda x: -x[0])
            for total_score, overlap, task_hits, nid, node in backfill_candidates[:6]:
                base_affinity = min(60 + total_score * 5, 78)
                reason_parts = []
                if overlap:
                    reason_parts.append(f"技能画像与该方向有 {overlap} 项重合")
                if task_hits:
                    reason_parts.append(
                        f"项目/实习经历与该岗位核心任务有 {task_hits} 项匹配"
                    )
                enriched.append(
                    {
                        "role_id": nid,
                        "label": node.get("label", nid),
                        "affinity_pct": base_affinity,
                        "matched_skills": [],
                        "gap_skills": (node.get("must_skills") or [])[:4],
                        "gap_hours": 0,
                        "zone": node.get("zone", "safe"),
                        "salary_p50": node.get("salary_p50", 0),
                        "reason": "；".join(reason_parts)
                        or f"技能画像与该方向有 {overlap} 项重合",
                        "channel": "growth",
                        "career_level": node.get("career_level", 0),
                        "replacement_pressure": node.get("replacement_pressure", 50),
                        "human_ai_leverage": node.get("human_ai_leverage", 50),
                    }
                )
            logger.info("Full backfill: added %d candidates", len(enriched))

            # ── Add promotion targets（应届生不加，避免混淆）──────────
            if exp_years >= 1:
                graph_edges = get_graph_edges()
                rec_ids = {r["role_id"] for r in enriched}
                promotion_targets = set()
                for e in graph_edges:
                    if e.get("edge_type") == "vertical" and e["source"] in rec_ids:
                        promotion_targets.add(e["target"])
                for e in graph_edges:
                    if e.get("edge_type") == "vertical" and e["source"] == node_id:
                        promotion_targets.add(e["target"])
                for pid in promotion_targets:
                    if pid in rec_ids:
                        continue
                    pn = graph_nodes.get(pid, {})
                    if not pn:
                        continue
                    cl = pn.get("career_level", 0) or 0
                    if exp_years <= 1 and cl > 3:
                        continue
                    if exp_years <= 3 and cl > 4:
                        continue
                    enriched.append(
                        {
                            "role_id": pid,
                            "label": pn.get("label", pid),
                            "affinity_pct": 0,
                            "matched_skills": [],
                            "gap_skills": pn.get("must_skills", [])[:4],
                            "gap_hours": 0,
                            "zone": pn.get("zone", "safe"),
                            "salary_p50": pn.get("salary_p50", 0),
                            "reason": "晋升方向",
                            "channel": "promotion",
                            "career_level": cl,
                            "replacement_pressure": pn.get("replacement_pressure", 50),
                            "human_ai_leverage": pn.get("human_ai_leverage", 50),
                        }
                    )

            # ── Programmatic job_target override (triple insurance) ────────────────
            # Locator re-ranking may have pushed the job_target role down or out.
            # Force it to rank #1 with affinity >= 88, same as _generate_recommendations.
            job_target = profile_data.get("job_target", "") or ""
            target_role_id = find_role_id_for_job_target(job_target)
            if target_role_id and target_role_id in graph_nodes:
                existing_ids = [r["role_id"] for r in enriched]
                if target_role_id in existing_ids:
                    idx = existing_ids.index(target_role_id)
                    target_rec = enriched.pop(idx)
                    target_rec["affinity_pct"] = max(
                        target_rec.get("affinity_pct", 0), 88
                    )
                    target_rec["channel"] = "entry"
                    target_rec["reason"] = (
                        target_rec.get("reason")
                        or f"与求职意向「{job_target}」高度吻合"
                    )
                    enriched.insert(0, target_rec)
                else:
                    node = graph_nodes[target_role_id]
                    enriched.insert(
                        0,
                        {
                            "role_id": target_role_id,
                            "label": node.get("label", target_role_id),
                            "affinity_pct": 88,
                            "matched_skills": [],
                            "gap_skills": node.get("must_skills", [])[:4],
                            "gap_hours": 0,
                            "zone": node.get("zone", "safe"),
                            "salary_p50": node.get("salary_p50", 0),
                            "reason": f"与求职意向「{job_target}」高度吻合",
                            "channel": "entry",
                            "career_level": node.get("career_level", 0),
                            "replacement_pressure": node.get(
                                "replacement_pressure", 50
                            ),
                            "human_ai_leverage": node.get("human_ai_leverage", 50),
                        },
                    )
                logger.info(
                    "Auto-locate job_target override: moved %s to rank #1 (job_target=%s)",
                    target_role_id,
                    job_target,
                )

            profile = db.query(Profile).filter(Profile.id == profile_id).first()
            if profile:
                p_hash = profile_hash(profile_data)
                rec_resp = {
                    "recommendations": enriched,
                    "user_skill_count": len(skills),
                }
                logger.info(
                    "[AUTO-LOCATE-SAVED] profile_id=%d top_rec=%r job_target=%r",
                    profile_id,
                    enriched[0]["label"] if enriched else "none",
                    profile_data.get("job_target", ""),
                )

        db.commit()
        # Cache only after successful commit to avoid inconsistency on rollback
        if profile:
            _save_rec_cache(profile, p_hash, rec_resp, db)
            db.commit()
        return {"node_id": node_id, "label": node_label}
    except Exception as e:
        import traceback

        print(f"[auto_locate] FAILED for user={user_id}: {e}")
        traceback.print_exc()
