# -*- coding: utf-8 -*-
"""Action plan builder for career development reports."""
from __future__ import annotations

from backend.services.report.data import (
    _user_skill_set,
    _PROJECT_SKILL_HINTS,
    _skill_matches,
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
    milestone_1 = "完成简历重塑与诊断，启动第一批核心技能补缺"
    milestone_2 = (
        f"补齐 {'、'.join(missing_skill_names)} 等核心技能缺口，建立可验证的项目或学习成果"
        if missing_skill_names
        else "补齐核心技能缺口，建立可验证的项目或学习成果"
    )
    milestone_3 = "完善项目展示与面试准备，达成目标岗位投递或获得 offer"

    stages = [
        {
            "stage": 1,
            "label": "短期夯实",
            "duration": "1-3个月",
            "milestone": milestone_1,
            "items": stage_items[1],
        },
        {
            "stage": 2,
            "label": "中期实战",
            "duration": "3-6个月",
            "milestone": milestone_2,
            "items": stage_items[2],
        },
        {
            "stage": 3,
            "label": "长期冲刺",
            "duration": "6-12个月",
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
