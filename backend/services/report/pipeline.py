# -*- coding: utf-8 -*-
"""Report pipeline — main entry points for career development reports."""
from __future__ import annotations

import copy
import json
import logging
import openai
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

from backend.services.report import data as _report_data

from backend.services.report import scoring
from backend.services.report import skill_gap
from backend.services.report import action_plan
from backend.services.report import career_alignment
from backend.services.report import narrative
from backend.services.report import summarize
from backend.skills._loader import SkillOutputParseError

logger = logging.getLogger(__name__)


def _parse_data(data_json: str) -> dict:
    """Parse a report's data_json field into a dict."""
    try:
        if isinstance(data_json, dict):
            return data_json
        return json.loads(data_json or "{}")
    except Exception:
        return {}


def _parse_profile(profile_json: str) -> dict:
    try:
        return json.loads(profile_json or "{}")
    except Exception:
        return {}


def generate_report(user_id: int, db) -> dict:
    """
    Generate a complete career development report for the current user.

    Returns the report data dict (to be serialized into Report.data_json).
    Raises ValueError if prerequisite data is missing.
    """
    # Always reload level_skills so changes from enrich scripts are picked up
    # without requiring a full server restart.
    try:
        loaders._LEVEL_SKILLS = json.loads((loaders._DATA_DIR / "level_skills.json").read_text(encoding="utf-8"))
    except Exception:
        pass
    _report_data._load_static()

    from backend.db_models import (
        Profile, CareerGoal, GrowthSnapshot, ProjectRecord,
    )

    # 1. Load profile
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        raise ValueError("no_profile")

    profile_data = _parse_profile(profile.profile_json)

    # 2. Load active career goal (skip empty/placeholder goals — user hasn't picked a target yet)
    goal = (
        db.query(CareerGoal)
        .filter(
            CareerGoal.user_id == user_id,
            CareerGoal.profile_id == profile.id,
            CareerGoal.is_active == True,
            CareerGoal.target_node_id != "",
            CareerGoal.target_node_id.isnot(None),
        )
        .order_by(CareerGoal.is_primary.desc(), CareerGoal.set_at.desc())
        .first()
    )
    if not goal:
        raise ValueError("no_goal")

    node_id = goal.target_node_id
    node = _report_data.get_graph_nodes().get(node_id)
    if not node:
        raise ValueError(f"unknown_node:{node_id}")

    # 3. Load growth snapshots (for curve + potential scoring)
    snapshots = (
        db.query(GrowthSnapshot)
        .filter(GrowthSnapshot.profile_id == profile.id)
        .order_by(GrowthSnapshot.created_at.asc())
        .limit(20)
        .all()
    )

    current_readiness = float(snapshots[-1].readiness_score) if snapshots else 0.0
    first_readiness = float(snapshots[0].readiness_score) if snapshots else 0.0
    growth_delta = current_readiness - first_readiness

    growth_curve = [
        {
            "date": s.created_at.strftime("%m/%d") if s.created_at else "",
            "score": round(float(s.readiness_score), 1),
        }
        for s in snapshots
    ]

    # 5. Load projects
    projects = (
        db.query(ProjectRecord)
        .filter(ProjectRecord.user_id == user_id)
        .all()
    )

    # 5b. Also read profile_json.projects — resume-extracted project descriptions.
    #     Primary project evidence for students who haven't entered growth log projects.
    profile_projects_raw: list[str] = []
    if isinstance(profile_data.get("projects"), list):
        profile_projects_raw = [p for p in profile_data["projects"] if isinstance(p, str) and p.strip()]

    # Extract a short display name from a project description.
    import re as _re
    def _short_proj_name(desc: str) -> str:
        # Core noun phrase extraction from a project description sentence.
        # Strategy: find the last significant noun phrase (技术名词) in the first clause.
        before_punct = _re.split(r'[，。,.、；]', desc)[0].strip()
        # Pattern 1: "实现(了/的)? <name>" at end of clause (up to 20 chars to handle longer names)
        m = _re.search(r'实现(?:了|的)?\s*(.{4,20}？)$', before_punct)
        if m:
            candidate = m.group(1).strip()
            candidate = _re.sub(r'^[的了地一个款]{1,3}', '', candidate).strip()
            if len(candidate) >= 4:
                return candidate
        # Pattern 2: "的 <tech-name>" where tech-name ends the clause (e.g. "基于X的C++高性能网络库")
        m2 = _re.search(r'的\s*((?:[A-Za-z+#]+\s*)?[\u4e00-\u9fff]{2,}[\u4e00-\u9fff\w+# ]*)$', before_punct)
        if m2:
            candidate = m2.group(1).strip()
            if 4 <= len(candidate) <= 20:
                return candidate
        # Fallback: last 12 chars, strip leading connectors
        raw = before_punct[-12:].strip() if len(before_punct) > 12 else before_punct
        return _re.sub(r'^[的了地是]{1,2}\s*', '', raw).strip()

    profile_proj_descs: list[dict] = [
        {"name": _short_proj_name(desc), "desc": desc}
        for desc in profile_projects_raw[:4]
    ]

    # 5d. Merge ProjectRecord list with profile_proj_descs for downstream use
    #     (reverse skill gap check + action plan + narrative generation).
    class _ProfileProj:
        """Minimal proxy so profile_json projects look like ProjectRecord."""
        def __init__(self, name: str, desc: str):
            self.name = name
            self.skills_used: list[str] = []
            self.status = "in_progress"
            self._desc = desc

    merged_projects = list(projects) + [
        _ProfileProj(pp["name"], pp["desc"])
        for pp in profile_proj_descs
        if not any(p.name == pp["name"] for p in projects)
    ]

    # 5c. Rule-based skill extraction from description text.
    #     Scan each description for the user's own resume skills — if a skill name
    #     appears in the description text, it is considered "practiced" (no LLM needed,
    #     no timeout risk). LLM is used as an optional enrichment afterward.
    user_skills_raw = _report_data._user_skill_set(profile_data)  # normalized lowercase set

    def _matches_in_text(skill_norm: str, text_norm: str) -> bool:
        """Exact substring match, plus 2-char semantic-head match for Chinese compounds.
        E.g. '网络编程' (skill) matches a text that contains '网络' even if not '网络编程'.
        The 2-char rule is limited to purely-Chinese compound skills to avoid false positives
        on short ASCII tokens (C++, STL, Git …).
        """
        if len(skill_norm) > 1 and skill_norm in text_norm:
            return True
        # Chinese compound fallback: e.g. '网络编程' → '网络', '性能优化' → '性能'
        if (len(skill_norm) >= 3
                and all('\u4e00' <= c <= '\u9fff' for c in skill_norm[:2])
                and skill_norm[:2] in text_norm):
            return True
        return False

    _desc_practiced: set[str] = set()
    for desc in profile_projects_raw:
        desc_norm = shared._norm_skill(desc)
        for skill in user_skills_raw:
            if _matches_in_text(shared._norm_skill(skill), desc_norm):
                _desc_practiced.add(skill)  # keep original casing from user_skills_raw

    # Also scan growth log project names/descriptions
    for p in projects:
        if p.name:
            pname_norm = shared._norm_skill(p.name)
            for skill in user_skills_raw:
                if _matches_in_text(shared._norm_skill(skill), pname_norm):
                    _desc_practiced.add(skill)

    logger.info("Rule-based desc scan: found practiced skills %s", _desc_practiced)

    # 6. Extract proficiency sets: rule-based desc scan + explicit skills_used
    practiced: set[str] = set()
    completed_practiced: set[str] = set()

    for s in _desc_practiced:
        practiced.add(s.lower().strip())

    for p in projects:
        explicit = [s for s in (p.skills_used or []) if isinstance(s, str) and s.strip()]
        for s in explicit:
            practiced.add(s.lower().strip())
        if getattr(p, "status", "") == "completed":
            for s in explicit:
                completed_practiced.add(s.lower().strip())

    # 6b. 合并的技能推断 + embedding 预筛：并发跑
    # - merged skill-inference：同时做开放提取 + 已声明技能校验（双任务单次调用）
    # - embedding pre-pass：语义相似度匹配 uncovered claimed 技能到项目
    # 两者互不依赖，结果取并集加入 practiced 集合。
    _user_skills_all = list(_report_data._user_skill_set(profile_data))
    _texts_to_infer = profile_projects_raw[:4] + [p.name for p in projects if not p.skills_used and p.name]
    _uncovered = [s for s in _user_skills_all if not shared._skill_in_set(s, practiced)]

    def _run_merged_skill_inference() -> tuple[list[str], list[str]]:
        """Returns (extracted_skills, validated_claimed)."""
        if not _texts_to_infer:
            return [], []
        try:
            from backend.skills import invoke_skill
            claimed_line = "、".join(_uncovered) if _uncovered else "（无）"
            resp = invoke_skill(
                "skill-inference",
                projects_text="\n".join(f"- {t[:200]}" for t in _texts_to_infer),
                claimed_skills_list=claimed_line,
            )
            if isinstance(resp, dict):
                skills = [s for s in (resp.get("skills") or []) if isinstance(s, str)]
                validated = [s for s in (resp.get("validated_claimed") or []) if isinstance(s, str)]
                # 把 LLM 可能自造的新技能过滤掉（validated_claimed 必须在 _uncovered 里）
                uncovered_set = {s.lower().strip() for s in _uncovered}
                validated = [s for s in validated if s.lower().strip() in uncovered_set]
                return skills, validated
            # 兼容老输出结构：裸数组 / 只含 skills 的 dict
            if isinstance(resp, list):
                return [s for s in resp if isinstance(s, str)], []
            return [], []
        except Exception as e:
            logger.debug("merged skill-inference skipped: %s", e)
            return [], []

    def _run_embedding_prepass() -> list[str]:
        """Returns list of skills to add to practiced (semantically matched to some project)."""
        if not _uncovered or not profile_proj_descs:
            return []
        class _EarlyProj:
            def __init__(self, name: str, desc: str):
                self.name = name
                self.skills_used: list[str] = []
                self._desc = desc
        _early_proj_objs = [_EarlyProj(pp["name"], pp["desc"]) for pp in profile_proj_descs]
        _early_proj_objs += [p for p in projects if getattr(p, "skills_used", None)]
        try:
            _embed_pre = skill_gap._embed_classify_skills(_uncovered, _early_proj_objs)
            return [sk for sk, pj in _embed_pre.items() if pj is not None]
        except Exception as e:
            logger.debug("embedding pre-pass skipped: %s", e)
            return []

    with ThreadPoolExecutor(max_workers=2) as _early_exec:
        _f_merged = _early_exec.submit(_run_merged_skill_inference)
        _f_embed = _early_exec.submit(_run_embedding_prepass)
        _extracted, _validated_claimed = _f_merged.result()
        _embed_matches = _f_embed.result()

    for s in _extracted:
        practiced.add(s.lower().strip())
    for s in _validated_claimed:
        practiced.add(s.lower().strip())
    for s in _embed_matches:
        practiced.add(s.lower().strip())

    if _extracted:
        logger.info("[skill-inference] extracted from text: %s", _extracted)
    if _validated_claimed:
        logger.info("[skill-inference] validated claimed: %s", _validated_claimed)
    if _embed_matches:
        logger.info("Embedding pre-pass practiced additions: %s", _embed_matches)

    # 6d. Reverse skill gap check: scan project texts for keywords that imply
    #     coverage of required skills, even if the user didn't list them in skills.

    _node_skill_names: list[str] = []
    _tiers = node.get("skill_tiers") or {}
    for _tier in ("core", "important", "bonus"):
        for _s in _tiers.get(_tier, []):
            _name = _s.get("name") if isinstance(_s, dict) else _s
            if _name:
                _node_skill_names.append(_name)
    for _s in node.get("must_skills", []) or []:
        if _s and _s not in _node_skill_names:
            _node_skill_names.append(_s)

    _all_project_text = " ".join(
        [pp.get("name", "") + " " + pp.get("desc", "") for pp in profile_proj_descs]
        + [getattr(p, "name", "") + " " + getattr(p, "_desc", "") for p in merged_projects]
    ).lower()

    for _req_skill in _node_skill_names:
        if shared._skill_matches(_req_skill, _user_skills_all) or shared._skill_in_set(_req_skill, practiced):
            continue
        _hints = shared._PROJECT_SKILL_HINTS.get(_req_skill, [])
        if any(_h in _all_project_text for _h in _hints):
            practiced.add(_req_skill.lower().strip())

    # 7. Compute four dimensions
    foundation_score = scoring._score_foundation(profile_data, node)
    skills_score = scoring._score_skills(profile_data, node, practiced, completed_practiced)
    qualities_score = None
    potential_score = scoring._score_potential(
        snapshots, projects, float(goal.transition_probability or 0)
    )

    four_dim = {
        "foundation": foundation_score,
        "skills": skills_score,
        "qualities": qualities_score,
        "potential": potential_score,
    }
    match_score = scoring._weighted_match_score(four_dim)

    # 7. Market signals
    family_name = _report_data.get_node_to_family().get(node_id)
    market_info: dict | None = _report_data.get_market().get(family_name) if family_name else None

    # 8. Skill gap analysis
    all_node_skills = []
    for tier in ("core", "important", "bonus"):
        for s in (node.get("skill_tiers", {}).get(tier) or []):
            if isinstance(s, dict) and s.get("name"):
                all_node_skills.append(s["name"])
            elif isinstance(s, str) and s:
                all_node_skills.append(s)
    text_practiced = skill_gap._extract_practiced_from_profile_text(
        profile_data, all_node_skills
    )
    if text_practiced:
        logger.info("[skill_gap] extracted %d skills from profile text: %s",
                    len(text_practiced), sorted(text_practiced))

    _skill_gap = skill_gap._build_skill_gap(
        profile_data, node, practiced, completed_practiced,
        extra_practiced=text_practiced,
    )

    # Runtime gap refine: LLM-based pseudo-gap filtering
    _skill_gap = skill_gap._refine_gap_with_llm(
        _skill_gap,
        profile_data=profile_data,
        target_label=goal.target_label,
    )

    # 8b. Load job applications for personalization
    from backend.db_models import JobApplication as _JobApplication
    applications = (
        db.query(_JobApplication)
        .filter(_JobApplication.user_id == user_id)
        .order_by(_JobApplication.created_at.desc())
        .limit(20)
        .all()
    )

    # 8c. Extract claimed-but-unverified core/important skills
    claimed_skills: list[str] = []
    if _skill_gap:
        for m in _skill_gap.get("matched_skills", []):
            if m.get("status") == "claimed" and m.get("tier") in ("core", "important"):
                claimed_skills.append(m["name"])

    # ── 新增：构造中间 JSON ─────────────────────────────────────────
    from backend.db_models import Report
    prev_report = (
        db.query(Report)
        .filter(Report.user_id == user_id)
        .order_by(Report.created_at.desc())
        .first()
    )
    summary = summarize.build_report_summary(
        user_id=user_id,
        profile=profile,
        db=db,
        prev_report=prev_report,
        skill_gap_current=_skill_gap,
    )

    # ── 准备 enriched_missing / report_skill_gap（纯 Python，毫秒级）──
    # 提前算好，differentiation worker 要用，同时 report_skill_gap 最后组装 payload 要用。
    project_recs_raw = node.get("project_recommendations", [])[:3]
    top_missing_raw = _skill_gap.get("top_missing", []) if _skill_gap else []
    enriched_projects, enriched_missing, project_mismatch = skill_gap._build_skill_fill_path_map(
        project_recs_raw, top_missing_raw
    )
    report_skill_gap = copy.deepcopy(_skill_gap) if _skill_gap else None
    if report_skill_gap is not None:
        report_skill_gap["top_missing"] = enriched_missing

    # ── 后段 6 个独立 LLM 调用：并发执行 ──
    # 它们都只依赖 summary / _skill_gap / profile / node / market_info（前面都已算好），
    # 互不依赖。串行耗时约 230s，并发后瓶颈 ≈ 最慢那个。

    def _worker_action_plan():
        try:
            raw = _invoke_action_plan_with_retry(
                target_label=goal.target_label,
                node_requirements_line=_format_node_requirements(node),
                market_line=narrative._format_market(market_info),
                summary_json=json.dumps(_slim_summary_for_action_plan(summary), ensure_ascii=False),
                prev_recommendations_block=_format_prev_recs(summary["prev_report_recommendations"]),
                completed_block=_format_completed(summary["completed_since_last_report"]),
            )
            return _coerce_action_plan(raw)
        except Exception as e:
            logger.warning("action-plan skill failed after retry, fallback to rule-based: %s", e)
            return action_plan._build_action_plan(
                gap_skills=goal.gap_skills or [],
                top_missing=_skill_gap.get("top_missing", []) if _skill_gap else [],
                node_id=node_id,
                node_label=goal.target_label,
                profile_data=profile_data,
                current_readiness=current_readiness,
                claimed_skills=claimed_skills,
                projects=merged_projects,
                applications=applications,
                profile_proj_descs=profile_proj_descs,
            )

    def _worker_narrative():
        return narrative._generate_narrative(
            target_label=goal.target_label,
            summary=summary,
            education_line=narrative._format_education(profile_data.get("education")),
            market_line=narrative._format_market(market_info),
        )

    def _worker_diagnosis():
        # SQLAlchemy session 非线程安全，线程内独立开一条
        from backend.db import SessionLocal
        _db = SessionLocal()
        try:
            return narrative._diagnose_profile(
                profile_data=profile_data,
                projects=projects,
                node_label=goal.target_label,
                db=_db,
            )
        finally:
            _db.close()

    def _worker_career_alignment():
        try:
            return career_alignment._build_career_alignment(
                profile_data=profile_data,
                projects=projects,
                graph_nodes=loaders._load_graph_nodes(),
                target_node_id=node_id,
                summary=summary,
            )
        except Exception as e:
            logger.warning("Career alignment build failed: %s", e)
            # 硬兜底：绝不返回 None，避免前端显示「数据不足」的硬编码 UI
            return {
                "observations": "基于当前档案标签，可初步观察与目标岗位的技能重叠情况。",
                "alignments": [{
                    "node_id": node_id,
                    "label": goal.target_label,
                    "score": 0.5,
                    "evidence": "用户已标定该方向为目标岗位",
                    "gap": "建议补充可量化的项目成果和技术文档以提升对齐度。",
                }],
                "cannot_judge": ["晋升节奏、团队匹配度等需要入职后才能判断的维度"],
            }

    def _worker_differentiation():
        return _build_differentiation_advice(
            target_label=goal.target_label,
            baseline=node.get("differentiation_advice", ""),
            summary=summary,
            top_missing=enriched_missing,
        )

    def _worker_market_narrative():
        return _build_market_narrative(
            target_label=goal.target_label,
            market_info=market_info,
            node=node,
            summary=summary,
        )

    # chapter4-intro 依赖 action_plan_data，单独在并发后运行
    def _worker_chapter4_intro(ap_data: dict) -> str:
        return _build_chapter4_intro(
            target_label=goal.target_label,
            action_plan_data=ap_data,
            summary=summary,
        )

    _parallel_start = time.time()
    with ThreadPoolExecutor(max_workers=6) as executor:
        f_action = executor.submit(_worker_action_plan)
        f_narrative = executor.submit(_worker_narrative)
        f_diagnosis = executor.submit(_worker_diagnosis)
        f_alignment = executor.submit(_worker_career_alignment)
        f_diff = executor.submit(_worker_differentiation)
        f_market = executor.submit(_worker_market_narrative)

        action_plan_data = f_action.result()
        narrative_text = f_narrative.result()
        diagnosis = f_diagnosis.result()
        career_alignment_data = f_alignment.result()
        differentiation_advice = f_diff.result()
        market_narrative = f_market.result()
    logger.info(
        "[pipeline] 6 parallel LLM tasks finished in %.1fs",
        time.time() - _parallel_start,
    )

    # chapter4-intro：在行动计划生成后串行调用（依赖 stages 内容）
    chapter4_intro = _worker_chapter4_intro(action_plan_data)

    # 10. Delta vs previous report (依赖 action_plan_data，必须在并发之后)
    delta = None
    if prev_report:
        prev_data = _parse_data(prev_report.data_json)
        prev_score = prev_data.get("match_score", 0)
        prev_skills_matched = set()
        for m in (prev_data.get("skill_gap", {}).get("matched_skills", [])):
            prev_skills_matched.add(m.get("name", "").lower())

        new_skills_matched = set()
        for m in (_skill_gap.get("matched_skills", [])):
            new_skills_matched.add(m.get("name", "").lower())

        gained_skills = [s for s in new_skills_matched if s not in prev_skills_matched and s]

        # Plan progress from ActionPlanV2
        plan_progress = None
        try:
            from backend.db_models import ActionPlanV2, ActionProgress
            latest_plan = (
                db.query(ActionPlanV2)
                .filter(ActionPlanV2.profile_id == profile.id)
                .order_by(ActionPlanV2.generated_at.desc())
                .first()
            )
            if latest_plan:
                all_plans = db.query(ActionPlanV2).filter(
                    ActionPlanV2.profile_id == profile.id,
                    ActionPlanV2.report_key == latest_plan.report_key,
                ).all()
                progress = db.query(ActionProgress).filter(
                    ActionProgress.profile_id == profile.id,
                    ActionProgress.report_key == latest_plan.report_key,
                ).first()
                checked = progress.checked if progress else {}
                total_items = 0
                done_items = 0
                for p in all_plans:
                    content = p.content if isinstance(p.content, dict) else json.loads(p.content or "{}")
                    items = content.get("items", [])
                    total_items += len(items)
                    done_items += sum(1 for it in items if checked.get(it.get("id", "")))
                plan_progress = {"done": done_items, "total": total_items}
        except Exception:
            pass

        # First pending SKILL/PROJECT task (prefer actionable over prep tasks)
        next_action = None
        _fallback_action = None
        stages = action_plan_data.get("stages", [])
        for stg in stages:
            for item in stg.get("items", []):
                if item.get("done", False):
                    continue
                if item.get("type") in ("skill", "project"):
                    next_action = item.get("text", "")
                    break
                elif not _fallback_action:
                    _fallback_action = item.get("text", "")
            if next_action:
                break
        if not next_action:
            next_action = _fallback_action

        # Pending improvement items: pull concrete task text, not abstract skill names
        pending_improvements: list[str] = []
        for stg in stages:
            for item in stg.get("items", []):
                if item.get("done", False):
                    continue
                if item.get("type") in ("skill", "project") and len(pending_improvements) < 3:
                    pending_improvements.append(item.get("text", ""))
        # Fallback: if no skill/project tasks, use skill names
        if not pending_improvements:
            pending_improvements = [s["name"] for s in _skill_gap.get("top_missing", [])[:3]]

        delta = {
            "prev_score": prev_score,
            "score_change": match_score - prev_score,
            "prev_date": prev_report.created_at.isoformat() if prev_report.created_at else "",
            "gained_skills": gained_skills[:5],
            "still_missing": pending_improvements,
            "plan_progress": plan_progress,
            "next_action": next_action,
        }

    # 13. Assemble report payload
    report_data = {
        "version": "1.0",
        "report_type": "long",
        "student": {
            "user_id": user_id,
            "profile_id": profile.id,
        },
        "target": {
            "node_id": node_id,
            "label": goal.target_label,
            "zone": goal.target_zone,
        },
        "match_score": match_score,
        "four_dim": four_dim,
        "narrative": narrative_text,
        "diagnosis": diagnosis,
        "market": {
            "demand_change_pct": market_info.get("demand_change_pct", 0) if market_info else None,
            "salary_cagr": market_info.get("salary_cagr", 0) if market_info else None,
            "salary_p50": node.get("salary_p50", 0),
            "timing": market_info.get("timing", "good") if market_info else "good",
            "timing_label": market_info.get("timing_label", "") if market_info else "",
        },
        "market_narrative": market_narrative,
        "skill_gap": report_skill_gap,
        "growth_curve": growth_curve,
        "action_plan": action_plan_data,
        "delta": delta,
        "soft_skills": node.get("soft_skills", {}),
        "career_alignment": career_alignment_data,
        "differentiation_advice": differentiation_advice,
        "ai_impact_narrative": node.get("ai_impact_narrative", ""),
        "project_recommendations": enriched_projects,
        "project_mismatch": project_mismatch,
        "summary": summary,
        "chapter_narratives": {
            "chapter-4": chapter4_intro,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    return report_data


def _slim_summary_for_action_plan(summary: dict) -> dict:
    """为 action-plan SKILL 裁剪 summary，只保留 LLM 真正需要的关键字段。

    去掉的：
    - growth_entries（近30天原文全量，可能几十条，占 context 大头）
    - skill_deltas.four_dim_trend（历史曲线数组，对行动计划无帮助）
    - signals 下的 raw 原文字段

    保留的：
    - profile_core（最重要：项目 / 工作经历 / 教育 / 技能）
    - milestones（最近5条，提供时间锚）
    - skill_deltas（去掉 four_dim_trend）
    - signals（application + interview 信号，裁掉重度嵌套字段）
    - window / version / completed_since_last_report / prev_report_recommendations
    """
    slim: dict[str, Any] = {
        "version": summary.get("version"),
        "window": summary.get("window"),
        "profile_core": summary.get("profile_core"),
        # 只取最近 5 条里程碑，给时间锚用
        "milestones": (summary.get("milestones") or [])[:5],
        # skill_deltas 去掉四维趋势数组（数据量大，对行动计划无意义）
        "skill_deltas": {
            k: v for k, v in (summary.get("skill_deltas") or {}).items()
            if k != "four_dim_trend"
        },
        # signals：保留聚合数字，去掉 raw / debriefs 原文
        "signals": _slim_signals(summary.get("signals") or {}),
        "completed_since_last_report": summary.get("completed_since_last_report"),
        "prev_report_recommendations": summary.get("prev_report_recommendations"),
    }
    # growth_entries 只保留最近5条，且每条截断原文到 400 字（给更多上下文）
    entries = (summary.get("growth_entries") or [])[:5]
    slim["growth_entries"] = [
        {k: (v[:400] if isinstance(v, str) and k in ("content", "note", "reflection") else v)
         for k, v in e.items()}
        for e in entries
    ]
    return slim


def _slim_signals(signals: dict) -> dict:
    """保留 signals 里的聚合数字，裁掉原文数组。"""
    out: dict[str, Any] = {}
    app = signals.get("application") or {}
    out["application"] = {
        k: v for k, v in app.items()
        if k not in ("recent_companies", "recent_entries")
    }
    iv = signals.get("interview") or {}
    out["interview"] = {
        k: v for k, v in iv.items()
        if k not in ("debriefs", "raw_reflections")
    }
    # 其余 key 直接透传
    for k, v in signals.items():
        if k not in ("application", "interview"):
            out[k] = v
    return out


def _build_market_narrative(
    target_label: str,
    market_info: dict | None,
    node: dict,
    summary: dict,
) -> str:
    """Generate a prose paragraph about the user's market situation.
    Returns empty string on failure (frontend falls back to old marketBits)."""
    try:
        from backend.skills import invoke_skill

        salary_p50 = node.get("salary_p50", 0)
        mi = market_info or {}
        demand_label = mi.get("demand_label", "暂无需求走势数据")
        salary_label = mi.get("salary_label", "暂无薪资趋势数据")
        timing_label = mi.get("timing_label", "暂无入场时机判断")

        app = summary.get("signals", {}).get("application", {})
        iv = summary.get("signals", {}).get("interview", {})

        parts: list[str] = []
        app_count = app.get("count_in_window", 0)
        if app_count > 0:
            funnel = app.get("funnel", {})
            parts.append(
                f"近期投了 {app_count} 家，"
                f"{funnel.get('interviewed', 0)} 家到面试阶段，"
                f"{funnel.get('rejected', 0)} 家被拒"
            )
        iv_count = iv.get("count_in_window", 0)
        if iv_count > 0:
            latest = iv.get("latest") or {}
            if latest.get("company"):
                parts.append(
                    f"最近面试在 {latest['company']}（{latest.get('round', '')}），"
                    f"自评 {latest.get('self_rating', '一般')}"
                )
        user_market_signal = "；".join(parts) + "。" if parts else "暂无投递和面试记录。"

        ai_label = mi.get("ai_label", "暂无 AI 影响数据")
        ai_impact = node.get("ai_impact_narrative", "暂无该方向的 AI 影响分析")

        text = invoke_skill(
            "market-narrative",
            target_label=target_label,
            salary_p50=salary_p50,
            demand_label=demand_label,
            salary_label=salary_label,
            timing_label=timing_label,
            ai_label=ai_label,
            ai_impact_narrative=ai_impact[:500],
            user_market_signal=user_market_signal,
        )
        result = text.strip() if isinstance(text, str) else ""
        return result if len(result) >= 30 else ""
    except Exception as e:
        logger.warning("market-narrative skill failed: %s", e)
        return ""


def _build_differentiation_advice(
    target_label: str,
    baseline: str,
    summary: dict,
    top_missing: list[dict],
) -> str:
    """Generate per-user Chapter III narrative via the differentiation skill.
    Falls back to the graph.json baseline text on any failure."""
    try:
        from backend.skills import invoke_skill

        top_missing_lines = []
        for m in (top_missing or [])[:5]:
            name = m.get("name", "") if isinstance(m, dict) else str(m)
            tier = m.get("tier", "") if isinstance(m, dict) else ""
            if name:
                top_missing_lines.append(
                    f"- {name}" + (f"（{tier}）" if tier else "")
                )
        top_missing_block = "\n".join(top_missing_lines) or "（暂无明确缺口）"

        still_claimed_line = "（已移除——请根据 summary_json 中的 profile_core.projects 自行判断技能是否有实践证据）"

        pain_points = (
            summary.get("signals", {}).get("interview", {}).get("pain_points", []) or []
        )
        pain_points_line = "；".join(pain_points[:5]) or "（本期无面试记录）"

        text = invoke_skill(
            "differentiation",
            target_label=target_label,
            baseline_differentiation=(baseline or "（岗位侧暂无通用差异化建议）")[:600],
            summary_json=json.dumps(summary, ensure_ascii=False)[:3000],
            top_missing_block=top_missing_block,
            still_claimed_only_line=still_claimed_line,
            pain_points_line=pain_points_line,
        )
        result = text.strip() if isinstance(text, str) else ""
        if len(result) < 100:
            logger.warning("differentiation skill returned suspiciously short text (%d chars), falling back", len(result))
            return baseline
        return result
    except Exception as e:
        logger.warning("differentiation skill failed, falling back to graph baseline: %s", e)
        return baseline


def _invoke_action_plan_with_retry(max_retries=1, **kwargs):
    import time
    from backend.skills import invoke_skill

    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return invoke_skill("action-plan", **kwargs)
        except (openai.APITimeoutError, SkillOutputParseError) as e:
            last_exc = e
            logger.warning("action-plan attempt %d/%d failed: %s: %s",
                          attempt + 1, max_retries + 1, type(e).__name__, e)
            if attempt < max_retries:
                time.sleep(2)
                continue
        except Exception as e:
            raise
    raise last_exc


def _format_node_requirements(node: dict) -> str:
    tiers = node.get("skill_tiers", {})
    core = [s.get("name") if isinstance(s, dict) else s for s in tiers.get("core", [])][:5]
    return f"核心技能：{', '.join(core) or '（未定义）'}"


def _format_prev_recs(recs: list[str]) -> str:
    if not recs:
        return "（这是第一份报告，无上次建议）"
    return "\n".join(f"- {r}" for r in recs[:6])


def _format_completed(items: list[str]) -> str:
    if not items:
        return "（本期无已完成的旧建议）"
    return "\n".join(f"- {it}" for it in items)


_FIELD_NAME_LEAK_PATTERNS: list[tuple[str, str]] = [
    # 反引号包着的字段名：`profile.projects[0]` → 你简历上的项目
    (r"`profile\.projects?\[\d+\]`", "你简历上的项目"),
    (r"`profile_core\.projects?`", "你简历上的项目"),
    (r"`profile\.work_experience(?:\[\d+\])?`", "你的工作经历"),
    (r"`profile_core\.work_experience`", "你的工作经历"),
    (r"`profile\.education`", "你的学历背景"),
    (r"`profile_core\.education`", "你的学历背景"),
    (r"`profile_core\.personal_statement`", "你的个人陈述"),
    (r"`growth_entries?`", "你的成长档案"),
    (r"`growth_entry:[A-Z0-9\-]+`", "某条成长档案记录"),
    (r"`skill_deltas?`", "技能档案"),
    (r"`skill_delta:still_claimed_only:[^`]+`", "这个还没证据的声明技能"),
    (r"`milestones?`", "你的里程碑"),
    (r"`milestone:[A-Z0-9\-]+`", "某个里程碑"),
    (r"`claimed_only`", "仅凭简历声明"),
    (r"`still_claimed_only`", "仍停留在简历声明"),
    (r"`completed_practiced`", "已完成项目里出现过"),
    (r"`evidence_ref`", "证据出处"),
    # 无反引号的裸字段名：profile.projects[0] → 你简历上的项目
    (r"\bprofile\.projects?\[\d+\]", "你简历上的项目"),
    (r"\bprofile_core\.projects?\b", "你简历上的项目"),
    (r"\bprofile\.work_experience(?:\[\d+\])?", "你的工作经历"),
    (r"\bprofile_core\.work_experience\b", "你的工作经历"),
    (r"\bprofile\.education\b", "你的学历背景"),
    (r"\bprofile_core\.education\b", "你的学历背景"),
    (r"\bprofile_core\.personal_statement\b", "你的个人陈述"),
    (r"\bgrowth_entries?\b", "你的成长档案"),
    (r"\bskill_deltas?\b", "技能档案"),
    (r"\bmilestones?\b", "你的里程碑"),
    (r"\bclaimed_only\b", "仅凭简历声明"),
    (r"\bstill_claimed_only\b", "仍停留在简历声明"),
]


def _sanitize_field_leaks(text: str) -> str:
    """把漏进正文的代码风格字段名换成自然中文。LLM 兜底，防止 observation 出现 `profile.projects[0]`。"""
    import re
    if not text:
        return text
    out = text
    for pat, repl in _FIELD_NAME_LEAK_PATTERNS:
        out = re.sub(pat, repl, out)
    # 清理替换后可能产生的多余空格 / 标点
    out = re.sub(r"\s+", " ", out).strip()
    out = re.sub(r"\s*([，。、；：！？])", r"\1", out)
    return out


def _coerce_action_plan(raw: dict) -> dict:
    """兜底 observation / action 字段，保证老数据和新数据结构一致。

    不再强制补齐 3 个 stages——SKILL 允许信号稀疏时只返回 1-2 个阶段，
    前端 ChapterIV.tsx 按 items 非空过滤。
    """
    stages = raw.get("stages", []) or []
    for stg in stages:
        # 阶段级文本也做一次清洗（label / milestone 有时会漏字段名）
        if stg.get("label"):
            stg["label"] = _sanitize_field_leaks(stg["label"])
        if stg.get("milestone"):
            stg["milestone"] = _sanitize_field_leaks(stg["milestone"])
        for it in stg.get("items", []):
            # 新字段兜底：老模型可能只给 text，没给 observation/action
            obs = it.get("observation") or it.get("text", "")
            act = it.get("action") or ""
            it["observation"] = _sanitize_field_leaks((obs or "").strip())
            it["action"] = _sanitize_field_leaks((act or "").strip())
            if it.get("tag"):
                it["tag"] = _sanitize_field_leaks(it["tag"])
            # 兼容字段：保留 text = observation
            it["text"] = it["observation"]
            if "evidence_ref" not in it:
                it["evidence_ref"] = ""
    return {
        "stages": stages,
        # 兼容字段：skills/project/job_prep 从 stages 里展平
        "skills": [it for s in stages for it in s.get("items", []) if it.get("type") == "skill"],
        "project": [it for s in stages for it in s.get("items", []) if it.get("type") == "project"],
        "job_prep": [it for s in stages for it in s.get("items", []) if it.get("type") == "job_prep"],
    }


def polish_narrative(narrative: str, target_label: str) -> str:
    """Re-polish an existing narrative via LLM."""
    try:
        from backend.skills import invoke_skill
        return invoke_skill("polish", target_label=target_label, narrative=narrative)
    except Exception as e:
        logger.warning("Polish failed: %s", e)
        return narrative


def _build_chapter4_intro(
    target_label: str,
    action_plan_data: dict,
    summary: dict,
) -> str:
    """Generate a prose intro paragraph for Chapter IV via the chapter4-intro skill.
    Falls back to empty string on failure (frontend gracefully hides it)."""
    try:
        from backend.skills import invoke_skill

        stages = action_plan_data.get("stages", []) or []
        stages_summary_lines = []
        for stg in stages:
            label = stg.get("label", "")
            milestone = stg.get("milestone", "")
            if label:
                stages_summary_lines.append(
                    f"- 阶段{stg.get('stage', '')}「{label}」"
                    + (f"：里程碑 → {milestone}" if milestone else "")
                )
        stages_summary = "\n".join(stages_summary_lines) or "（无阶段数据）"

        # 提取处境快照：成长档案活跃度 + 面试信号 + 技能缺口摘要
        signals = summary.get("signals", {}) or {}
        app = signals.get("application", {}) or {}
        iv = signals.get("interview", {}) or {}
        milestones = (summary.get("milestones") or [])[:3]

        snapshot_parts: list[str] = []
        app_count = app.get("count_in_window", 0)
        if app_count:
            funnel = app.get("funnel", {}) or {}
            snapshot_parts.append(
                f"近期投了 {app_count} 家，"
                f"{funnel.get('interviewed', 0)} 家到面试，"
                f"{funnel.get('rejected', 0)} 家被拒"
            )
        iv_count = iv.get("count_in_window", 0)
        if iv_count:
            latest = iv.get("latest") or {}
            pain = iv.get("pain_points") or []
            snapshot_parts.append(
                f"面试 {iv_count} 次，最近在 {latest.get('company', '未知公司')}"
                + (f"，高频卡点：{'; '.join(pain[:2])}" if pain else "")
            )
        for ms in milestones:
            event = ms.get("event") or ms.get("label") or ""
            if event:
                snapshot_parts.append(f"里程碑：{event}")
        # 成长档案活跃度
        entries = summary.get("growth_entries") or []
        if entries:
            snapshot_parts.append(f"成长档案近期有 {len(entries)} 条记录")

        situation_snapshot = "；".join(snapshot_parts) or "暂无活跃信号"

        result = invoke_skill(
            "chapter4-intro",
            target_label=target_label,
            stages_summary=stages_summary,
            situation_snapshot=situation_snapshot,
        )
        text = result.strip() if isinstance(result, str) else ""
        return text if len(text) >= 40 else ""
    except Exception as e:
        logger.warning("chapter4-intro skill failed: %s", e)
        return ""
