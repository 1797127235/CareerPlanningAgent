# -*- coding: utf-8 -*-
"""Career alignment analysis for career development reports."""
from __future__ import annotations

import json
import logging
from typing import Any

from backend.services.report.loaders import _load_graph_nodes

logger = logging.getLogger(__name__)


def _canon_skill(s: Any) -> str:
    """技能名规范化：lower + strip，兼容非字符串输入。"""
    if isinstance(s, dict):
        s = s.get("name")
    if not isinstance(s, str):
        s = str(s) if s is not None else ""
    return s.strip().lower()


def _preselect_alignment_candidates(
    user_skills: list[str],
    graph_nodes: list[dict],
    top_k: int = 15,
) -> list[dict]:
    """基于技能 overlap 预选候选节点。"""
    user_skill_set = {_canon_skill(s) for s in user_skills if s}
    if not user_skill_set:
        return []

    scored = []
    for node in graph_nodes:
        # 从 skill_tiers 或 must_skills 提取节点要求的技能名集合
        node_skills = set()
        tiers = node.get("skill_tiers", {}) or {}
        for tier in ("core", "important", "bonus"):
            for s in tiers.get(tier, []) or []:
                name = s.get("name") if isinstance(s, dict) else s
                if name:
                    node_skills.add(_canon_skill(name))
        for s in node.get("must_skills", []) or []:
            node_skills.add(_canon_skill(s))

        if not node_skills:
            continue

        overlap = len(user_skill_set & node_skills)
        scored.append({
            "node_id": node.get("node_id"),
            "label": node.get("label"),
            "role_family": node.get("role_family"),
            "career_level": node.get("career_level"),
            "must_skills": list(node_skills)[:8],
            "_overlap": overlap,
        })

    scored.sort(key=lambda x: x["_overlap"], reverse=True)
    # 取 top_k；为 LLM 留对比视角，保留 2-3 个 overlap=0 的节点
    top = scored[:top_k - 3]
    filler = [s for s in scored[top_k:] if s["_overlap"] == 0][:3]
    return top + filler


def _normalize_project_sources(profile_data: dict, projects: list) -> list[dict]:
    """合并两类项目来源，统一为 {name, desc, source} 字典列表。

    - profile_data.projects (简历提取): str 或 {name, description} dict
    - projects (ProjectRecord from 成长档案): ORM 对象

    来源标签让 LLM 看清哪些是简历陈述、哪些是档案追踪数据。
    """
    pool: list[dict] = []

    # ── 简历来源 ──
    for p in (profile_data.get("projects") or []):
        if isinstance(p, str) and p.strip():
            pool.append({"name": "简历项目", "desc": p.strip(), "source": "resume"})
        elif isinstance(p, dict):
            _desc = p.get("description")
            _name = p.get("name")
            desc = (_desc.strip() if isinstance(_desc, str) else str(_desc)).strip() if _desc else ""
            name = (_name.strip() if isinstance(_name, str) else str(_name)).strip() if _name else ""
            name = name or "简历项目"
            if desc or name:
                pool.append({"name": name, "desc": desc or name, "source": "resume"})

    # ── 成长档案来源 ──
    for p in (projects or []):
        desc = (getattr(p, "description", "") or "").strip()
        name = (getattr(p, "name", "") or "未命名").strip()
        if desc or name:
            pool.append({"name": name, "desc": desc or name, "source": "growth_log"})

    return pool


def _build_alignment_ctx(skills, projects, soft_skills, candidates, target_node_id, profile_data=None, summary=None):
    # 合并简历 + 成长档案项目
    all_projects = _normalize_project_sources(profile_data or {}, projects)

    proj_lines = []
    for p in all_projects[:8]:  # 最多 8 个项目，防 prompt 过长
        tag = "简历" if p["source"] == "resume" else "档案"
        proj_lines.append(f"- [{tag}] [{p['name']}] {p['desc'][:220]}")
    projects_list = "\n".join(proj_lines) or "（无项目数据）"

    # 软技能
    ss_lines = []
    for k, v in (soft_skills or {}).items():
        if k.startswith("_"):
            continue
        if isinstance(v, (int, float)):
            ss_lines.append(f"- {k}: {int(v)}/100")
    soft_skills_summary = "\n".join(ss_lines) or "（无软技能评估）"

    # 候选节点
    cand_list = []
    for c in candidates:
        cand_list.append({
            "node_id": c["node_id"],
            "label": c["label"],
            "role_family": c.get("role_family", ""),
            "career_level": c.get("career_level", ""),
            "key_skills": c["must_skills"][:5],
        })
    candidates_json = json.dumps(cand_list, ensure_ascii=False)

    target_hint = ""
    if target_node_id:
        target_hint = f"学生目前标定的目标岗位 node_id: {target_node_id}（若此岗位在候选列表中，请给出对齐评估；若不在，请观察其他对齐方向）"

    # 只取技能名，丢掉 level / 其他字段——防 LLM 把 intermediate/beginner/familiar
    # 这些内部枚举值搬进正文（用户看到会觉得像数据导出而不是自然叙事）
    def _skill_name_only(s: Any) -> str:
        if isinstance(s, dict):
            return str(s.get("name", "")).strip()
        return str(s).strip()
    skill_names = [n for n in (_skill_name_only(s) for s in (skills or [])[:30]) if n]
    skills_list = "、".join(skill_names)

    # 行为信号格式化
    summary = summary or {}
    signals = summary.get("signals", {})
    interview = signals.get("interview", {}) or {}
    application = signals.get("application", {}) or {}

    latest = interview.get("latest") or {}
    if latest and latest.get("company"):
        interview_line = (
            f"最近面试：{latest.get('company')} {latest.get('round')}，"
            f"自评{latest.get('self_rating')}，结果{latest.get('result')}"
        )
    else:
        interview_line = "近期暂无面试记录"

    directions = application.get("directions", []) or []
    if directions:
        application_directions = "；".join(
            f"{d['label']}（{d['count']} 次）" for d in directions[:3]
        )
    else:
        application_directions = "暂无投递记录"

    pain_points = interview.get("pain_points", []) or []
    if pain_points:
        pain_points_line = "\n".join(f"- {p}" for p in pain_points[:5])
    else:
        pain_points_line = "（暂无明确痛点记录）"

    return {
        "candidates_json": candidates_json,
        "target_node_id": target_hint,
        "skills_list": skills_list,
        "projects_list": projects_list,
        "soft_skills_summary": soft_skills_summary,
        "interview_line": interview_line,
        "application_directions": application_directions,
        "pain_points_line": pain_points_line,
    }


def _build_career_alignment(
    profile_data: dict,          # profile.profile_json 解析后的 dict
    projects: list,              # ProjectRecord list
    graph_nodes: list[dict],     # data/graph.json 的 nodes 数组
    target_node_id: str | None = None,  # 学生当前的目标岗位（如有）
    summary: dict | None = None,
) -> dict | None:
    """
    基于学生数据做方向对齐分析。输出绑定 graph.json node_id。

    返回 schema：
    {
        "observations": str,        # 对学生数据的事实观察，2-3 句
        "alignments": [              # 最多 3 条，按 score 降序
            {
                "node_id": str,      # 必须在 graph_nodes 里存在
                "label": str,        # 从 graph_nodes 回填，不来自 LLM
                "score": float,      # 0-1 clip
                "evidence": str,     # 引用学生具体项目或数字
                "gap": str,          # 还差什么（可为空字符串）
            }
        ],
        "cannot_judge": list[str],  # 显式声明无法判断的维度
    }

    返回 None 表示数据不足（项目 < 2 或技能 < 5 或无软技能数据）。
    """
    # ── [Step 1] 数据准备 ──
    skills = profile_data.get("skills", []) or []
    soft_skills = profile_data.get("soft_skills", {}) or {}
    merged_projects = _normalize_project_sources(profile_data, projects)
    projects_count = len(merged_projects)

    has_enough_data = projects_count >= 2 and len(skills) >= 5
    if not has_enough_data:
        logger.info(
            "Career alignment: limited data (merged_projects=%d, skills=%d)",
            projects_count, len(skills)
        )

    # ── [Step 2] 候选节点预选 ──
    candidates = _preselect_alignment_candidates(skills, graph_nodes, top_k=15)
    if not candidates:
        # 连候选都没有时，基于目标节点（如有）或热门节点做一个最小 fallback
        if target_node_id:
            target_node = next((n for n in graph_nodes if n.get("node_id") == target_node_id), None)
            if target_node:
                candidates = [{
                    "node_id": target_node_id,
                    "label": target_node.get("label", target_node_id),
                    "role_family": target_node.get("role_family", ""),
                    "career_level": target_node.get("career_level", ""),
                    "must_skills": list(target_node.get("must_skills", []))[:8],
                    "_overlap": 0,
                }]
        if not candidates and graph_nodes:
            # 最后 resort：随便取第一个有 label 的节点
            first = graph_nodes[0]
            candidates = [{
                "node_id": first.get("node_id", ""),
                "label": first.get("label", ""),
                "role_family": first.get("role_family", ""),
                "career_level": first.get("career_level", ""),
                "must_skills": list(first.get("must_skills", []))[:8],
                "_overlap": 0,
            }]

    # ── [Step 2] 构造 Prompt ctx ──
    ctx = _build_alignment_ctx(
        skills=skills,
        projects=projects,
        soft_skills=soft_skills,
        candidates=candidates,
        target_node_id=target_node_id,
        profile_data=profile_data,  # 让 prompt builder 也能读简历项目
        summary=summary,
    )

    # ── [Step 3] 调用 LLM ──
    parsed: dict | None = None
    try:
        from backend.skills import invoke_skill
        parsed = invoke_skill("career-alignment", **ctx)
    except Exception as e:
        logger.warning("Career alignment LLM call failed: %s", e)

    # ── [Step 4] 护栏 Validate ──
    node_map = {n.get("node_id"): n for n in graph_nodes if n.get("node_id")}
    validated: list[dict] = []
    if parsed:
        for a in parsed.get("alignments", []):
            nid = a.get("node_id", "")
            if nid not in node_map:
                logger.warning("Career alignment: LLM invented node_id '%s', dropped", nid)
                continue
            a["label"] = node_map[nid].get("label", nid)
            try:
                s = float(a.get("score", 0))
                a["score"] = max(0.0, min(1.0, s))
            except (ValueError, TypeError):
                a["score"] = 0.0
            validated.append(a)
        validated.sort(key=lambda x: x["score"], reverse=True)

    # ── [Step 5] Fallback ──
    # 如果 LLM 失败或返回为空，基于 candidates overlap 生成简单的非 LLM fallback，
    # 避免前端因为返回 None 而显示「数据不足」的硬编码 UI。
    if not validated:
        logger.info("Career alignment: using non-LLM fallback based on skill overlap")
        user_skill_set = {_canon_skill(s) for s in skills}
        for c in candidates[:3]:
            nid = c.get("node_id")
            if not nid or nid not in node_map:
                continue
            c_node = node_map[nid]
            node_skills = set()
            tiers = c_node.get("skill_tiers") or {}
            for tier in ("core", "important", "bonus"):
                for s in tiers.get(tier, []) or []:
                    name = s.get("name") if isinstance(s, dict) else s
                    if name:
                        node_skills.add(_canon_skill(name))
            for s in c_node.get("must_skills", []) or []:
                node_skills.add(_canon_skill(s))
            overlap_skills = user_skill_set & node_skills
            total_skills = len(node_skills) or 1
            score = min(len(overlap_skills) / total_skills * 1.5, 0.85)
            validated.append({
                "node_id": nid,
                "label": c_node.get("label", nid),
                "score": round(score, 2),
                "evidence": f"技能标签中包含 {', '.join(list(overlap_skills)[:4]) or '部分'} 相关技能" if overlap_skills else "技能画像与该方向有一定交集",
                "gap": "项目描述中缺少与该方向核心要求直接对应的深度实践证据，建议补充可量化的项目成果。",
            })

    observations = ""
    if parsed and parsed.get("observations"):
        observations = parsed.get("observations", "")
    elif validated:
        top_label = validated[0].get("label", "目标方向")
        observations = (
            f"基于当前技能画像，{top_label} 等方向与简历标签有一定重叠。"
            "项目经验的深度和可验证的技术文档，是影响对齐度的主要变量。"
        )

    return {
        "observations": observations,
        "alignments": validated[:3],
        "cannot_judge": parsed.get("cannot_judge", []) if parsed else ["晋升节奏、团队匹配度等需要入职后才能判断的维度"],
    }
