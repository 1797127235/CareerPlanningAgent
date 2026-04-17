# -*- coding: utf-8 -*-
"""Action plan builder for career development reports."""
from __future__ import annotations

from backend.services.report.shared import (
    _user_skill_set,
    _PROJECT_SKILL_HINTS,
    _skill_matches,
)
from backend.services.report.skill_gap import (
    _skill_action,
    _has_hardcoded_guidance,
    _generate_skill_actions_llm,
)


def _build_action_plan(
    gap_skills: list[str],
    top_missing: list[dict],
    node_id: str,
    node_label: str,
    profile_data: dict,
    current_readiness: float,
    claimed_skills: list[str] | None = None,
    projects: list | None = None,
    applications: list | None = None,
    profile_proj_descs: list[dict] | None = None,
) -> dict:
    """
    Build a descriptive action plan.
      - skills:   observational gap descriptions (no prescribed projects)
      - project:  directional guidance (no concrete project names)
      - job_prep: resume / application readiness observations
    """
    user_skills = _user_skill_set(profile_data)
    _proj_text = " ".join(pp.get("desc", "") for pp in (profile_proj_descs or [])).lower()

    # ── 1. Skill tasks ────────────────────────────────────────────────────────
    skill_tasks = []
    seen: set[str] = set()

    skill_pool: list[dict] = []
    for m in top_missing:
        name = m.get("name", "")
        freq = m.get("freq", 0)
        tier = m.get("tier", "important")
        fill_path = m.get("fill_path", "both")
        if name and name.lower() not in seen and not _skill_matches(name, user_skills):
            skill_pool.append({"name": name, "freq": freq, "tier": tier, "fill_path": fill_path})
            seen.add(name.lower())
    for s in gap_skills:
        if s.lower() not in seen and not _skill_matches(s, user_skills):
            skill_pool.append({"name": s, "freq": 0, "tier": "important", "fill_path": "both"})
            seen.add(s.lower())

    tier_order = {"core": 0, "important": 1, "bonus": 2}
    skill_pool.sort(key=lambda x: (tier_order.get(x["tier"], 1), -x["freq"]))

    for i, s in enumerate(skill_pool[:3]):
        name = s["name"]
        priority = "high" if s["tier"] == "core" or i == 0 else "medium"

        hints = _PROJECT_SKILL_HINTS.get(name, [name.lower()])
        covered_in_project = any(h in _proj_text for h in hints)

        if covered_in_project:
            if s["fill_path"] == "learn":
                text = f"你的项目经历已经涉及 {name}，有实践基础。下一步可以深入原理层面，把实战中踩过的坑和设计取舍整理成文档，面试时能讲出\"为什么这样做\"比\"做了什么\"更有说服力。"
            elif s["fill_path"] == "practice":
                text = f"你的项目经历已经涉及 {name}，有实践基础。如果能补充性能数据（QPS、延迟、内存占用等量化指标），简历和面试的说服力会更强。"
            else:
                text = f"你的项目经历已经涉及 {name}，有实践基础。下一步建议深入这个方向——补充量化数据或技术文档，把\"用过\"升级为\"深入理解\"。"
            tag = "深入方向"
        else:
            if s["fill_path"] == "learn":
                text = f"简历技能中包含 {name}，但项目描述中未见与之对应的具体应用场景，建议通过技术文档建立系统性理解。"
            elif s["fill_path"] == "practice":
                text = f"当前项目描述中未见 {name} 相关的具体技术关键词，建议通过搜索引擎或技术社区了解该方向在目标岗位中的考察重点。"
            else:
                text = f"当前项目描述中未见 {name} 相关的具体技术关键词，建议关注该方向在目标岗位中的实践形态和面试考察点。"
            tag = "面试追问点"

        skill_tasks.append({
            "id": f"skill_{name[:10].replace(' ', '_')}",
            "type": "skill",
            "sub_type": "learn",
            "text": text,
            "tag": tag,
            "skill_name": name,
            "priority": priority,
            "done": False,
        })

    # ── 2. Project task ───────────────────────────────────────────────────────
    truly_missing = [s for s in skill_pool if s.get("fill_path") in ("practice", "both")]
    top_skill_names = [s["name"] for s in truly_missing[:2]]

    has_metrics = any(
        d in _proj_text
        for d in ["qps", "latency", "用户", "日活", "准确率", "提升", "%", "倍", "ms", "tps", "吞吐"]
    )
    if not has_metrics:
        project_text = (
            "当前项目描述偏向'做了什么'，而缺少'做成了什么'的量化叙事。"
            "在简历中使用'动词+动作+数字'的 impact-first 结构，能显著提升通过初筛的概率。"
        )
    elif top_skill_names:
        project_text = (
            f"目标岗位看重 {'、'.join(top_skill_names)} 等方向的实战背景。"
            "可通过搜索引擎或技术社区了解该方向的典型项目形态和面试考察要点。"
        )
    else:
        project_text = (
            f"{node_label} 方向注重项目经验的深度。"
            "建议在已有实践基础上，关注量化成果、技术选型和性能数据等面试高频追问点。"
        )
    project_tasks = [{
        "id": "proj_main",
        "type": "project",
        "text": project_text,
        "tag": "实战方向参考" if has_metrics else "可量化缺失",
        "priority": "high",
        "done": False,
    }]

    # ── 3. Job prep tasks ────────────────────────────────────────────────────
    job_prep_tasks = []
    readiness_label = "完善" if current_readiness < 60 else "优化"

    job_prep_tasks.append({
        "id": "prep_resume",
        "type": "job_prep",
        "text": f"{readiness_label}简历：建议突出与 {node_label} 相关的技术关键词和可量化成果，让面试官在 10 秒内看到你的工程价值。",
        "tag": "求职必备",
        "priority": "high",
        "done": False,
    })

    app_count = len(applications or [])
    if app_count == 0:
        apply_text = "建立目标公司候选列表（5-10家），区分保底/目标/冲刺三档，技能补强完成后开始批量投递"
        apply_tag = "尚未开始投递"
    elif app_count < 5:
        apply_text = f"已投 {app_count} 家，建议扩大到 10+ 家，增加保底岗位比例，避免孤注一掷"
        apply_tag = f"已投 {app_count} 家"
    else:
        apply_text = f"已投 {app_count} 家，注意复盘无回音的原因——可能是简历筛选环节，建议对照岗位JD检查关键词覆盖"
        apply_tag = f"已投 {app_count} 家"

    job_prep_tasks.append({
        "id": "prep_apply",
        "type": "job_prep",
        "text": apply_text,
        "tag": apply_tag,
        "priority": "medium",
        "done": False,
    })

    # ── Assign phase and group into stages ──────────────────────────────────
    all_tasks = skill_tasks + project_tasks + job_prep_tasks

    for t in all_tasks:
        tid = t.get("id", "")
        ttype = t.get("type", "")
        sub = t.get("sub_type", "")

        t["deliverable"] = ""

        if sub == "learn" and ttype == "skill":
            t["phase"] = 2
        elif ttype == "project":
            t["phase"] = 2
        elif tid == "prep_resume":
            t["phase"] = 1
        elif tid.startswith("prep_apply") and app_count == 0:
            t["phase"] = 1
        elif tid.startswith("prep_apply") and app_count > 0:
            t["phase"] = 3
        else:
            t["phase"] = 1

    stage_items: dict[int, list[dict]] = {1: [], 2: [], 3: []}
    for t in all_tasks:
        stage_items[t["phase"]].append(t)

    missing_skill_names = [s["name"] for s in skill_pool[:2]]
    milestone_1 = "整理简历，确保技术关键词与目标岗位对齐"
    milestone_2 = (
        f"补齐 {'、'.join(missing_skill_names)} 等核心技能缺口，建立可验证的学习或实践证据"
        if missing_skill_names
        else "补齐核心技能缺口，建立可验证的学习或实践证据"
    )
    milestone_3 = "完善项目展示资料，开始目标岗位投递"

    stages = [
        {
            "stage": 1,
            "label": "立即整理",
            "duration": "0-2周",
            "milestone": milestone_1,
            "items": stage_items[1],
        },
        {
            "stage": 2,
            "label": "技能补强",
            "duration": "2-6周",
            "milestone": milestone_2,
            "items": stage_items[2],
        },
        {
            "stage": 3,
            "label": "项目冲刺+求职",
            "duration": "6-12周",
            "milestone": milestone_3,
            "items": stage_items[3],
        },
    ]

    return {
        "stages": stages,
        "skills":   skill_tasks,
        "project":  project_tasks,
        "job_prep": job_prep_tasks,
    }
    skill_pool: list[dict] = []
    for m in top_missing:
        name = m.get("name", "")
        freq = m.get("freq", 0)
        tier = m.get("tier", "important")
        if name and name.lower() not in seen and not _skill_matches(name, user_skills):
            skill_pool.append({"name": name, "freq": freq, "tier": tier})
            seen.add(name.lower())
    for s in gap_skills:
        if s.lower() not in seen and not _skill_matches(s, user_skills):
            skill_pool.append({"name": s, "freq": 0, "tier": "important"})
            seen.add(s.lower())

    tier_order = {"core": 0, "important": 1, "bonus": 2}
    skill_pool.sort(key=lambda x: (tier_order.get(x["tier"], 1), -x["freq"]))

    remaining_slots = max(0, 3 - len(skill_tasks))
    candidate_pool = skill_pool[:remaining_slots]

    # Pre-generate LLM guidance for skills not in hardcoded dict (single batch call)
    llm_uncovered = [
        s["name"] for s in candidate_pool
        if not _find_related_project(s["name"])[1] in ("recorded", "inferred")
        and not _has_hardcoded_guidance(s["name"])
    ]
    llm_guidance: dict[str, str] = _generate_skill_actions_llm(
        llm_uncovered, node_label, any_proj_names
    ) if llm_uncovered else {}

    for i, s in enumerate(candidate_pool):
        name = s["name"]
        freq_pct = int(s["freq"] * 100) if s["freq"] else 0
        freq_tag = f"JD 出现率 {freq_pct}%" if freq_pct > 0 else "目标岗位所需"
        priority = "high" if s["tier"] == "core" or i == 0 else "medium"
        # Check if an existing project already covers this "missing" skill
        related_proj, match_type = _find_related_project(name)
        if match_type in ("recorded", "inferred"):
            # User's project already demonstrates this skill — nudge to surface it on resume
            skill_tasks.append({
                "id": f"verify_{name[:10].replace(' ', '_')}",
                "type": "skill",
                "sub_type": "validate",
                "text": f"『{related_proj}』已经在做 {name}——把它加进简历技能栏，补写量化数据（如性能提升幅度、并发 QPS 等），让面试官看到实战深度",
                "tag": "实战已有，加入简历",
                "skill_name": name,
                "priority": priority,
                "done": False,
            })
        else:
            proj_ctx = any_proj_names[0] if any_proj_names else None
            # Use LLM-generated text if available, otherwise hardcoded dict / fallback
            action_text = llm_guidance.get(name) or _skill_action(name, proj=proj_ctx)
            skill_tasks.append({
                "id": f"skill_{name[:10].replace(' ', '_')}",
                "type": "skill",
                "sub_type": "learn",
                "text": action_text,
                "tag": freq_tag,
                "skill_name": name,
                "priority": priority,
                "done": False,
            })

    # ── 2. Project task ───────────────────────────────────────────────────────
    # Only reference skills that are genuinely missing (not embedding-covered)
    truly_missing = [
        s for s in skill_pool
        if _llm_coverage.get(s["name"]) is None  # embedding found no covering project
    ]
    top_skill_names = [s["name"] for s in truly_missing[:3]]

    # Determine best existing project to polish (prefer completed, else any)
    showcase_proj = (
        next((p.name for p in (projects or []) if getattr(p, "status", "") == "completed"), None)
        or (any_proj_names[0] if any_proj_names else None)
    )

    if showcase_proj and not top_skill_names:
        # User's projects already cover all missing skills → polish & publish
        project_text = (
            f"『{showcase_proj}』已有实战深度——"
            f"补写完整 README（含架构说明、性能数据）、添加单元测试，发布到 GitHub 作为核心展示项目"
        )
        project_tag = "打磨现有项目，提升简历含金量"
    elif showcase_proj and top_skill_names:
        tech_str = " + ".join(top_skill_names[:2])
        project_text = f"在『{showcase_proj}』基础上引入 {tech_str}，补写 README 和性能测试后推送 GitHub"
        project_tag = "基于现有项目扩展"
    elif top_skill_names:
        tech_str = " + ".join(top_skill_names[:2])
        project_text = f"用 {tech_str} 从零实现一个完整项目（含文档、代码、部署），发布到 GitHub"
        project_tag = "从零建立项目经验"
    else:
        project_text = f"独立完成一个 {node_label} 方向的实战项目，从需求到上线全流程，录入成长档案"
        project_tag = "建立项目经验"
    project_tasks = [{
        "id": "proj_main",
        "type": "project",
        "text": project_text,
        "tag": project_tag,
        "priority": "high",
        "done": False,
    }]

    # ── 3. Job prep tasks ────────────────────────────────────────────────────
    job_prep_tasks = []
    readiness_label = "完善" if current_readiness < 60 else "优化"

    # Personalize resume task based on actual projects
    if completed_proj_names:
        resume_detail = f"重点突出『{'』『'.join(completed_proj_names[:2])}』，量化技术成果（如性能提升、功能覆盖范围）"
    else:
        resume_detail = f"补充 {node_label} 相关项目经历，量化成果（如性能提升、功能覆盖范围）"

    job_prep_tasks.append({
        "id": "prep_resume",
        "type": "job_prep",
        "text": f"{readiness_label}简历：{resume_detail}",
        "tag": "求职必备",
        "priority": "high",
        "done": False,
    })

    # Application strategy based on actual application data
    app_count = len(applications or [])
    if app_count == 0:
        apply_text = "建立目标公司候选列表（5-10家），区分保底/目标/冲刺三档，技能补强完成后开始批量投递"
        apply_tag = "尚未开始投递"
    elif app_count < 5:
        apply_text = f"已投 {app_count} 家，建议扩大到 10+ 家，增加保底岗位比例，避免孤注一掷"
        apply_tag = f"已投 {app_count} 家"
    else:
        apply_text = f"已投 {app_count} 家，注意复盘无回音的原因——可能是简历筛选环节，建议对照岗位JD检查关键词覆盖"
        apply_tag = f"已投 {app_count} 家"

    job_prep_tasks.append({
        "id": "prep_apply",
        "type": "job_prep",
        "text": apply_text,
        "tag": apply_tag,
        "priority": "medium",
        "done": False,
    })

    # ── Assign phase and deliverable to each task, then group into stages ────

    all_tasks = skill_tasks + project_tasks + job_prep_tasks

    app_count = len(applications or [])

    # Assign phase + deliverable to each task
    for t in all_tasks:
        tid = t.get("id", "")
        ttype = t.get("type", "")
        sub = t.get("sub_type", "")

        # Deliverable
        if sub == "validate":
            t["deliverable"] = "更新后的简历技能栏截图"
        elif sub == "learn":
            t["deliverable"] = "用该技能做一个 demo 并写进项目描述"
        elif ttype == "project":
            t["deliverable"] = "GitHub 仓库链接 + README"
        elif tid == "prep_resume":
            t["deliverable"] = "更新后的简历 PDF"
        elif tid.startswith("prep_apply"):
            t["deliverable"] = "投递记录（成长档案中可查）"

        # Phase assignment
        if sub == "validate" or tid == "prep_resume":
            t["phase"] = 1
        elif tid.startswith("prep_apply") and app_count == 0:
            t["phase"] = 1
        elif sub == "learn":
            t["phase"] = 2
        elif ttype == "project":
            t["phase"] = 3
        elif tid.startswith("prep_apply") and app_count > 0:
            t["phase"] = 3
        else:
            # Fallback: job_prep tasks without specific rule go to stage 1
            t["phase"] = 1

    # Group into stages
    stage_items: dict[int, list[dict]] = {1: [], 2: [], 3: []}
    for t in all_tasks:
        stage_items[t["phase"]].append(t)

    # Build milestone text referencing user projects when available
    proj_name_ref = (
        completed_proj_names[0] if completed_proj_names
        else any_proj_names[0] if any_proj_names
        else None
    )

    if proj_name_ref:
        milestone_1 = f"『{proj_name_ref}』README 补全 + 简历更新"
    else:
        milestone_1 = "简历更新完成，已有项目补全 README"

    missing_skill_names = [s["name"] for s in skill_pool[:2]]
    if missing_skill_names:
        milestone_2 = f"补齐 {'、'.join(missing_skill_names)} 等核心技能缺口，有可量化学习产出"
    else:
        milestone_2 = "填补核心技能缺口，有可量化学习产出"

    if proj_name_ref:
        milestone_3 = f"『{proj_name_ref}』推上 GitHub，投递 10 家以上"
    else:
        milestone_3 = "项目推上 GitHub，投递 10 家以上"

    stages = [
        {
            "stage": 1,
            "label": "立即整理",
            "duration": "0-2周",
            "milestone": milestone_1,
            "items": stage_items[1],
        },
        {
            "stage": 2,
            "label": "技能补强",
            "duration": "2-6周",
            "milestone": milestone_2,
            "items": stage_items[2],
        },
        {
            "stage": 3,
            "label": "项目冲刺+求职",
            "duration": "6-12周",
            "milestone": milestone_3,
            "items": stage_items[3],
        },
    ]

    return {
        "stages": stages,
        # Keep old format for backward compatibility
        "skills":   skill_tasks,
        "project":  project_tasks,
        "job_prep": job_prep_tasks,
    }
