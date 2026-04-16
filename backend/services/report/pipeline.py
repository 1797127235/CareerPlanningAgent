# -*- coding: utf-8 -*-
"""Report pipeline — main entry points for career development reports."""
from __future__ import annotations

import copy
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from backend.services.report import shared
from backend.services.report import loaders
from backend.services.report import scoring
from backend.services.report import skill_gap
from backend.services.report import action_plan
from backend.services.report import career_alignment
from backend.services.report import narrative
from backend.services.report import summarize

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
    loaders._load_static()

    from backend.db_models import (
        Profile, CareerGoal, GrowthSnapshot, ProjectRecord,
    )

    # 1. Load profile
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        raise ValueError("no_profile")

    profile_data = _parse_profile(profile.profile_json)

    # 2. Load active career goal
    goal = (
        db.query(CareerGoal)
        .filter(
            CareerGoal.user_id == user_id,
            CareerGoal.profile_id == profile.id,
            CareerGoal.is_active == True,
        )
        .order_by(CareerGoal.is_primary.desc(), CareerGoal.set_at.desc())
        .first()
    )
    if not goal:
        raise ValueError("no_goal")

    node_id = goal.target_node_id
    node = loaders.get_graph_nodes().get(node_id)
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
    user_skills_raw = shared._user_skill_set(profile_data)  # normalized lowercase set

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

    # Optional LLM enrichment for skills NOT in user's resume (e.g. Reactor, epoll)
    _inferred_skills_from_text: list[str] = list(_desc_practiced)
    _texts_to_infer = profile_projects_raw[:4] + [p.name for p in projects if not p.skills_used and p.name]
    if _texts_to_infer:
        try:
            from backend.skills import invoke_skill
            _extra = invoke_skill(
                "skill-inference",
                projects_text="\n".join(f"- {t[:100]}" for t in _texts_to_infer),
            )
            if isinstance(_extra, list):
                _inferred_skills_from_text.extend(s for s in _extra if isinstance(s, str))
            elif isinstance(_extra, dict):
                for v in _extra.values():
                    if isinstance(v, list):
                        _inferred_skills_from_text.extend(s for s in v if isinstance(s, str))
        except Exception as _e:
            logger.debug("LLM skill enrichment skipped: %s", _e)

    # 6. Extract proficiency sets: rule-based desc scan + LLM enrichment + ProjectRecord
    practiced: set[str] = set()
    completed_practiced: set[str] = set()

    for s in _inferred_skills_from_text:
        practiced.add(s.lower().strip())

    for p in projects:
        explicit = [s for s in (p.skills_used or []) if isinstance(s, str) and s.strip()]
        for s in explicit:
            practiced.add(s.lower().strip())
        if getattr(p, "status", "") == "completed":
            for s in explicit:
                completed_practiced.add(s.lower().strip())

    # 6b. Embedding pre-pass: infer implicit skills not caught by rule-based scan.
    #     E.g. "Linux" and "STL" are implicit in any C++ network project even if
    #     not mentioned verbatim.  Run embeddings now so _build_skill_gap sees them
    #     as "practiced" rather than "claimed".
    _user_skills_all = list(shared._user_skill_set(profile_data))
    _uncovered = [s for s in _user_skills_all if not shared._skill_in_set(s, practiced)]
    if _uncovered and profile_proj_descs:
        # Build lightweight proxy objects for profile descriptions
        class _EarlyProj:
            def __init__(self, name: str, desc: str):
                self.name = name
                self.skills_used: list[str] = []
                self._desc = desc
        _early_proj_objs = [_EarlyProj(pp["name"], pp["desc"]) for pp in profile_proj_descs]
        _early_proj_objs += [p for p in projects if getattr(p, "skills_used", None)]
        _embed_pre = skill_gap._embed_classify_skills(_uncovered, _early_proj_objs)
        for _sk, _pj in _embed_pre.items():
            if _pj is not None:
                practiced.add(_sk.lower().strip())
        logger.info("Embedding pre-pass practiced additions: %s",
                    [k for k, v in _embed_pre.items() if v])

        # 6c. LLM 隐式技能推断 pre-pass：
        #     embedding 只能捕捉语义相似度，无法推理"C++ 网络库必然用 STL+Linux"
        #     这种技术栈依赖关系。让 LLM 读项目描述，显式推断隐式用到的技术。
        _still_uncovered = [
            s for s in _user_skills_all
            if not shared._skill_in_set(s, practiced)
        ]
        if _still_uncovered and profile_proj_descs:
            _llm_implicit = skill_gap._infer_implicit_skills_llm(
                _still_uncovered,
                profile_proj_descs,
            )
            for _sk in _llm_implicit:
                practiced.add(_sk.lower().strip())
            if _llm_implicit:
                logger.info("LLM implicit-skill inference added: %s", _llm_implicit)

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
    family_name = loaders.get_node_to_family().get(node_id)
    market_info: dict | None = loaders.get_market().get(family_name) if family_name else None

    # 8. Skill gap analysis
    _skill_gap = skill_gap._build_skill_gap(profile_data, node, practiced, completed_practiced)

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

    # ── Action plan ───────────────────────────────────────────────────────────
    try:
        from backend.skills import invoke_skill
        action_plan_data = invoke_skill(
            "action-plan",
            target_label=goal.target_label,
            node_requirements_line=_format_node_requirements(node),
            market_line=narrative._format_market(market_info),
            summary_json=json.dumps(summary, ensure_ascii=False),
            prev_recommendations_block=_format_prev_recs(summary["prev_report_recommendations"]),
            completed_block=_format_completed(summary["completed_since_last_report"]),
        )
        action_plan_data = _coerce_action_plan(action_plan_data)
    except Exception as e:
        logger.warning("action-plan skill failed, fallback to rule-based: %s", e)
        action_plan_data = action_plan._build_action_plan(
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

    # 10. Delta vs previous report
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

    # 10b. LLM narrative
    narrative_text = narrative._generate_narrative(
        target_label=goal.target_label,
        summary=summary,
        education_line=narrative._format_education(profile_data.get("education")),
        market_line=narrative._format_market(market_info),
    )

    # 10c. Profile diagnosis (档案体检 — content completeness check)
    diagnosis = narrative._diagnose_profile(
        profile_data=profile_data,
        projects=projects,
        node_label=goal.target_label,
        db=db,
    )

    # ── 方向对齐分析（LLM 分析 + graph 绑定）──
    try:
        career_alignment_data = career_alignment._build_career_alignment(
            profile_data=profile_data,
            projects=projects,
            graph_nodes=loaders._load_graph_nodes(),
            target_node_id=node_id,
            summary=summary,
        )
    except Exception as e:
        logger.warning("Career alignment build failed: %s", e)
        # 硬兜底：绝不返回 None，避免前端显示「数据不足」的硬编码 UI
        career_alignment_data = {
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

    # 12. Build enriched project recommendations + skill fill path map
    import copy
    project_recs_raw = node.get("project_recommendations", [])[:3]
    top_missing_raw = _skill_gap.get("top_missing", []) if _skill_gap else []

    enriched_projects, enriched_missing, project_mismatch = skill_gap._build_skill_fill_path_map(
        project_recs_raw, top_missing_raw
    )

    report_skill_gap = copy.deepcopy(_skill_gap) if _skill_gap else None
    if report_skill_gap is not None:
        report_skill_gap["top_missing"] = enriched_missing

    # 12b. Chapter III: personalized differentiation narrative via LLM.
    # Replaces the static graph.json node.differentiation_advice with a
    # per-user narrative grounded in summary + skill_gap. Falls back to the
    # graph.json text if the skill call fails.
    differentiation_advice = _build_differentiation_advice(
        target_label=goal.target_label,
        baseline=node.get("differentiation_advice", ""),
        summary=summary,
        top_missing=enriched_missing,
    )

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
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    return report_data


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

        still_claimed = summary.get("skill_deltas", {}).get("still_claimed_only", []) or []
        still_claimed_line = ", ".join(still_claimed[:8]) or "（无）"

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


_IMPERATIVE_PREFIXES = (
    "完成", "搭建", "实现", "编写", "学习", "掌握", "阅读",
    "深入", "用", "通过", "进行", "梳理", "配置", "部署",
    "建议你", "你应该", "你需要", "你必须", "最好", "先",
)


def _sanitize_action_text(text: str) -> str:
    t = text.strip()
    if any(t.startswith(p) for p in _IMPERATIVE_PREFIXES):
        return "结合当前方向的特点，探索适合自己的学习或实践路径。"
    return text


def _coerce_action_plan(raw: dict) -> dict:
    """确保 raw 至少有 stages[3]，每个 stage 有 items。缺的补空。"""
    stages = raw.get("stages", [])
    while len(stages) < 3:
        stages.append({
            "stage": len(stages) + 1,
            "label": ["立即整理", "技能补强", "项目冲刺与求职"][len(stages)],
            "duration": ["0-2周", "2-6周", "6-12周"][len(stages)],
            "milestone": "",
            "items": [],
        })
    # sanitize item texts and ensure evidence_ref exists
    for stg in stages[:3]:
        for it in stg.get("items", []):
            it["text"] = _sanitize_action_text(it.get("text", ""))
            if "evidence_ref" not in it:
                it["evidence_ref"] = ""
    return {
        "stages": stages[:3],
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
