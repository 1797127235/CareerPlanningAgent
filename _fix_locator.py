path = "/root/CareerPlanningAgent/backend/services/graph/locator.py"
with open(path, "r") as f:
    content = f.read()

# Fix 1: initialize enriched before the if block
old = """    # Cache recommendations from the same LLM call
    recs_raw = llm_result.get("recommendations", [])
    if recs_raw:"""
new = """    # Cache recommendations from the same LLM call
    recs_raw = llm_result.get("recommendations", [])
    enriched = []
    if recs_raw:"""
content = content.replace(old, new)

# Fix 2: add backfill when enriched is empty after LLM filtering
old2 = """            if backfilled:
                logger.info("Auto-locate backfill: added %d candidates (task+skill)", backfilled)

            # ── Add promotion targets"""

new2 = """            if backfilled:
                logger.info("Auto-locate backfill: added %d candidates (task+skill)", backfilled)

        # ── Fallback: if all LLM results were filtered, run skill-based backfill
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
                    text_parts.append(str(p.get("description", "") or p.get("highlights", "")).lower())
                elif isinstance(p, str):
                    text_parts.append(p.lower())
            for i in profile_data.get("internships", []):
                if isinstance(i, dict):
                    text_parts.append(str(i.get("role", "")).lower())
                    text_parts.append(str(i.get("description", "") or i.get("highlights", "")).lower())
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
                core_tasks = [t.strip() for t in node.get("core_tasks", []) if t and len(t.strip()) >= 3]
                expanded_tasks = _expand_chinese_tokens(core_tasks)
                task_hits = sum(1 for t in expanded_tasks if len(t) >= 2 and t in user_text_combined) if core_tasks else 0
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
                    reason_parts.append(f"项目/实习经历与该岗位核心任务有 {task_hits} 项匹配")
                enriched.append({
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
                })
            logger.info("Full backfill: added %d candidates", len(enriched))

            # ── Add promotion targets"""

content = content.replace(old2, new2)
with open(path, "w") as f:
    f.write(content)
print("fixed")
