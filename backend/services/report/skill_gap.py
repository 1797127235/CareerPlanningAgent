# -*- coding: utf-8 -*-
"""Skill gap analysis and action generation for career reports."""
from __future__ import annotations

import json
import logging
from typing import Any

from backend.services.report.shared import (
    _user_skill_set,
    _skill_proficiency,
    _skill_matches,
    _skill_in_set,
    _cosine_sim,
    _batch_embed,
)
from backend.services.report.loaders import _classify_fill_path

logger = logging.getLogger(__name__)


# Skill-specific learning guidance
_SKILL_GUIDANCE: dict[str, str] = {
    "typescript":    "完成 TypeScript 官方 Handbook 基础篇，重点练习泛型与接口定义",
    "react":         "跟着官方文档实现一个带状态管理的 React 应用（如 Todo / 日历）",
    "vue":           "用 Vue 3 Composition API 实现一个完整的前后端分离小项目",
    "python":        "用 Python 实现至少一个完整项目，涵盖文件操作、API 调用或数据处理",
    "docker":        "将现有项目容器化，编写 Dockerfile 并推送到 Docker Hub",
    "kubernetes":    "在本地搭建 minikube，完成一次服务部署与滚动更新实验",
    "git":           "梳理 Git 分支模型，练习 rebase、cherry-pick 等进阶操作",
    "mysql":         "设计一个包含至少 5 张表的数据库 Schema，练习复杂 JOIN 与索引优化",
    "redis":         "在项目中实践缓存穿透防护和分布式锁，理解 Redis 过期策略",
    "linux":         "掌握常用运维命令，完成一次从零部署应用到 Linux 服务器的全流程",
    "go":            "用 Go 实现一个 HTTP 服务，理解 goroutine 并发模型与接口设计",
    "rust":          "完成《Rust 程序设计语言》前 10 章，实现所有权模型的实践练习",
    "java":          "深入理解 JVM 内存模型，实现一个多线程场景的并发安全代码",
    "spring":        "用 Spring Boot 搭建一套完整 REST API，配合 MyBatis 完成 CRUD",
    "javascript":    "深入理解事件循环与异步机制，用原生 JS 实现一个完整功能模块",
    "css":           "掌握 Flexbox 与 Grid 布局，复现 3 个真实设计稿的响应式页面",
    "nginx":         "配置 Nginx 实现反向代理和静态资源托管，理解负载均衡原理",
    "jenkins":       "搭建一条包含构建、测试、部署的完整 CI/CD 流水线",
    "tensorflow":    "完成一个端到端的模型训练—评估—推理项目，理解数据预处理流程",
    "pytorch":       "用 PyTorch 实现一个图像分类或文本分类任务，记录实验报告",
    "sql":           "在真实数据集上练习窗口函数、子查询与执行计划分析",
    "spark":         "完成一个 Spark 批处理任务，理解 RDD 与 DataFrame 的性能差异",
    "aws":           "在 AWS 免费套餐上部署一个应用，实践 S3、EC2、RDS 基础操作",
    "微服务":         "将一个单体项目拆分为 2-3 个微服务，实现服务间通信与注册发现",
    # C++ 生态
    "高并发":         "在{proj}基础上用 wrk/ab 做压测，量化当前 QPS 和延迟基准，再对比引入多 Reactor 或 io_uring 后的提升幅度，把结果写进 README",
    "并发":           "在{proj}基础上用 wrk/ab 做压测，量化当前 QPS 和延迟基准，再对比引入多 Reactor 或 io_uring 后的提升幅度，把结果写进 README",
    "性能优化":       "用 perf/gprof 对{proj}做热点分析，找到最耗时的函数，优化后记录改动前后的延迟/吞吐量对比数据，加进项目 README",
    "内存管理":       "深入{proj}的内存分配策略，对比 tcmalloc/jemalloc 的 arena 设计差异，补写一篇内存碎片率和分配延迟的分析文档",
    "gdb":            "用 GDB 调试{proj}，练习断点、watchpoint、backtrace，记录一次完整调试过程并写进 README",
    "cmake":          "为{proj}配置完整 CMakeLists.txt，加入 AddressSanitizer/ThreadSanitizer 支持和 Google Test 单元测试",
    "协程":           "用 C++20 coroutine 改写{proj}的一个异步模块，压测对比协程 vs 线程池的延迟和 CPU 占用，记录实验数据",
    "分布式系统":      "在{proj}基础上实现简单的主从复制或 Raft 日志同步，理解分布式一致性的基础原理",
    "消息队列":       "在{proj}中实现无锁环形队列或集成 RabbitMQ，压测生产消费吞吐量并和加锁版本对比",
    "epoll":          "梳理{proj}中 epoll 事件循环的实现，补写 epoll ET/LT 模式对比测试和 EAGAIN 处理细节文档",
}


def _skill_action(skill: str, proj: str | None = None) -> str:
    """Return specific learning guidance for a skill, optionally referencing a project."""
    key = skill.lower()
    for k, v in _SKILL_GUIDANCE.items():
        if k in key:
            if proj and "{proj}" in v:
                return v.replace("{proj}", f"『{proj}』")
            elif "{proj}" in v:
                return v.replace("{proj}", "现有项目")
            return v
    # Not in hardcoded dict — caller should use _generate_skill_actions_llm batch instead.
    if proj:
        return f"结合『{proj}』，深入学习 {skill}，完成一个可量化效果的实验并录入成长档案"
    return f"针对 {skill} 选一个最核心的子方向，完成一个能量化效果的小型项目并录入成长档案"


def _has_hardcoded_guidance(skill: str) -> bool:
    """Return True if _SKILL_GUIDANCE has an entry for this skill."""
    key = skill.lower()
    return any(k in key for k in _SKILL_GUIDANCE)


def _generate_skill_actions_llm(
    skills: list[str],
    node_label: str,
    proj_names: list[str],
) -> dict[str, str]:
    """
    Single LLM call to generate personalized action text for skills not in _SKILL_GUIDANCE.
    Returns dict: skill → action text (20–60 chars, imperative, references projects when possible).
    Falls back to empty dict on any error (caller uses _skill_action fallback).
    """
    if not skills:
        return {}
    try:
        from backend.llm import get_llm_client, get_model
        proj_ctx = "、".join(f"『{p}』" for p in proj_names[:3]) if proj_names else "（暂无项目）"
        skills_list = "\n".join(f"- {s}" for s in skills)
        prompt = f"""你是职业规划顾问，为一名 {node_label} 方向的学生生成技能成长建议。
学生现有项目：{proj_ctx}

请为以下每个技能生成一条具体行动建议（20-60字，祈使句，尽量结合现有项目，强调可量化结果）：
{skills_list}

输出 JSON 对象，key 为技能名，value 为建议文本。只输出 JSON，不要解释。"""

        resp = get_llm_client(timeout=15).chat.completions.create(
            model=get_model("fast"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=600,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        if isinstance(result, dict):
            return {k: str(v) for k, v in result.items() if v}
    except Exception as e:
        logger.warning("_generate_skill_actions_llm failed: %s", e)
    return {}


_PROJECT_SKILL_EMBED_THRESHOLD = 0.55


def _build_skill_fill_path_map(
    project_recs: list[dict],
    top_missing: list[dict],
) -> tuple[list[dict], list[dict], bool]:
    """
    为每个 project 预计算 covered_skills；为每个 top_missing 预计算
    covered_by_project 和 fill_path。

    返回：(enriched_projects, enriched_missing, project_mismatch)
    project_mismatch = True 当且仅当过滤后没有任何 project 有非空 covered_skills。
    """
    if not project_recs or not top_missing:
        enriched_projects = [dict(p, covered_skills=[]) for p in project_recs]
        enriched_missing = [
            dict(m, covered_by_project=False, fill_path=_classify_fill_path(m.get("name", ""), False))
            for m in top_missing
        ]
        mismatch = len(project_recs) > 0 and not any(p["covered_skills"] for p in enriched_projects)
        return enriched_projects, enriched_missing, mismatch

    # 1) 准备文本
    project_texts = [f"{p.get('name', '')} {p.get('why', '')}".strip() for p in project_recs]
    missing_names = [m.get("name", "").strip() for m in top_missing]
    all_texts = project_texts + missing_names

    # 2) 批量 embedding
    embeddings = _batch_embed(all_texts)
    if embeddings is None:
        # API 失败：保守回退，全部认为无关联，但不标记 mismatch（避免污染语义）
        enriched_projects = [dict(p, covered_skills=[]) for p in project_recs]
        enriched_missing = [
            dict(m, covered_by_project=False, fill_path=_classify_fill_path(m.get("name", ""), False))
            for m in top_missing
        ]
        return enriched_projects, enriched_missing, False

    proj_embs = embeddings[:len(project_texts)]
    miss_embs = embeddings[len(project_texts):]

    # 3) 计算 project -> covered_skills
    enriched_projects: list[dict] = []
    for p, pe in zip(project_recs, proj_embs):
        covered: list[str] = []
        for m, me in zip(top_missing, miss_embs):
            sim = _cosine_sim(pe, me)
            if sim >= _PROJECT_SKILL_EMBED_THRESHOLD:
                covered.append(m["name"])
        enriched_projects.append(dict(p, covered_skills=covered))

    # 4) 过滤掉 covered_skills 为空的项目
    visible_projects = [p for p in enriched_projects if p["covered_skills"]]
    project_mismatch = len(visible_projects) == 0 and len(project_recs) > 0

    # 5) 计算 missing -> covered_by_project + fill_path
    #    以 visible_projects（过滤后）为准，判断该缺口是否被任一项目覆盖
    enriched_missing: list[dict] = []
    for m, me in zip(top_missing, miss_embs):
        covered_by_project = any(
            m["name"] in p["covered_skills"] for p in visible_projects
        )
        fill_path = _classify_fill_path(m.get("name", ""), covered_by_project)
        enriched_missing.append(dict(m, covered_by_project=covered_by_project, fill_path=fill_path))

    return enriched_projects, enriched_missing, project_mismatch


# Semantic similarity threshold: above this → project covers the skill
_EMBED_THRESHOLD = 0.65


def _embed_classify_skills(
    skill_names: list[str],
    projects: list,
) -> dict[str, str | None]:
    """
    Use embedding cosine similarity to determine which skills are already covered
    by existing projects — no hardcoded synonym tables, no chat-completion overhead.

    Each project is represented as: "<project_name>: <skills_used joined>".
    Skill names are embedded as-is.

    Returns dict: skill_name -> covering_project_name (None if not covered).
    Falls back to empty dict on any API error.
    """
    if not skill_names or not projects:
        return {}

    proj_texts = []
    for p in projects:
        skills_str = ', '.join(p.skills_used or [])
        # For _ProfileProj (resume-extracted), use description as richer context
        desc_str = getattr(p, '_desc', '') or ''
        body = skills_str or desc_str
        proj_texts.append(f"{p.name}: {body}".strip(": ") if body else p.name or "")
    all_texts = skill_names + proj_texts
    embeddings = _batch_embed(all_texts)
    if not embeddings or len(embeddings) != len(all_texts):
        return {}

    skill_embeds = embeddings[:len(skill_names)]
    proj_embeds  = embeddings[len(skill_names):]

    result: dict[str, str | None] = {}
    for skill, s_emb in zip(skill_names, skill_embeds):
        best_sim = 0.0
        best_proj = None
        for p, p_emb in zip(projects, proj_embeds):
            sim = _cosine_sim(s_emb, p_emb)
            if sim > best_sim:
                best_sim = sim
                best_proj = p.name
        result[skill] = best_proj if best_sim >= _EMBED_THRESHOLD else None
        logger.debug("Skill '%s' → '%s' (sim=%.3f)", skill, result[skill], best_sim)

    return result


def _infer_implicit_skills_llm(
    uncovered_skills: list[str],
    profile_proj_descs: list[dict],
) -> list[str]:
    """LLM 语义推理：哪些"未验证"技能实际上已隐含在项目描述里？

    embedding 相似度 < 0.65 会错过"C++ 网络库 → STL/Linux socket"这种
    技术栈依赖关系。用 LLM 做一轮显式推理，把"明显隐含在项目里"的技能
    从 claimed 拉到 practiced。

    返回：应该标为 practiced 的技能名列表（原样大小写，便于后续 set 匹配）。
    失败时返回空列表，不抛异常。
    """
    if not uncovered_skills or not profile_proj_descs:
        return []

    # 组装项目文本
    proj_lines = []
    for pp in profile_proj_descs[:6]:
        name = pp.get("name", "未命名")
        desc = pp.get("desc", "")[:250]
        if desc:
            proj_lines.append(f"- [{name}] {desc}")
    if not proj_lines:
        return []

    skills_str = "、".join(uncovered_skills)
    proj_block = "\n".join(proj_lines)

    prompt = f"""你是技术栈分析助手。任务：判断学生项目里**隐式使用了**下面哪些技术。

# 判定规则（严格）

1. 只有当项目**必然会用到**该技术时才返回（例如 C++ 网络库必然用 STL 容器 + Linux socket + 多线程）
2. 如果只是可能用到但不确定，**不要返回**
3. 不是跨领域关联（比如用 Python 不意味着会 R）
4. 基于技术常识推理，不要瞎猜

# 待判定技能列表
{skills_str}

# 学生项目
{proj_block}

# 输出格式（严格 JSON，不要多余文字）

{{
  "implicit_used": ["确认隐式用到的技能 1", "技能 2"],
  "reasoning": "一句话说明判定依据"
}}

只输出 JSON。"""

    try:
        from backend.llm import get_llm_client, get_model
        resp = get_llm_client(timeout=20).chat.completions.create(
            model=get_model("fast"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=400,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw.strip())
        implicit = parsed.get("implicit_used", []) or []
        # 只保留原列表里存在的技能，防 LLM 自造新技能名
        uncovered_set = {s.lower().strip() for s in uncovered_skills}
        result = [s for s in implicit if s.lower().strip() in uncovered_set]
        return result
    except Exception as e:
        logger.warning("Implicit skill inference failed: %s", e)
        return []


def _build_skill_gap(
    profile_data: dict,
    node: dict,
    practiced: set[str] | None = None,
    completed_practiced: set[str] | None = None,
) -> dict:
    """
    Build market-oriented skill gap analysis using JD frequency data from skill_tiers.

    Returns:
      core / important / bonus  — tier coverage stats {total, matched, pct, practiced_count, claimed_count}
      top_missing               — up to 8 missing skills sorted by JD freq desc
      matched_skills            — up to 10 skills user has, with proficiency status
      has_project_data          — whether any project evidence exists (affects badge display)
    """
    user_skills = _user_skill_set(profile_data)
    practiced = practiced or set()
    completed_practiced = completed_practiced or set()
    has_project_data = bool(practiced or completed_practiced)

    tiers = node.get("skill_tiers") or {}
    core      = tiers.get("core")      or []
    important = tiers.get("important") or []
    bonus     = tiers.get("bonus")     or []

    all_matched: list[dict] = []
    missing:     list[dict] = []

    def _process_tier(skills: list, tier_name: str) -> dict:
        total = len(skills)
        matched_list: list[dict] = []
        for s in skills:
            name = s.get("name", "")
            is_matched, status = _skill_proficiency(
                name, user_skills, practiced, completed_practiced, has_project_data
            )
            if is_matched:
                matched_list.append({
                    "name": name,
                    "tier": tier_name,
                    "status": status,
                    "freq": s.get("freq", 0),
                })
            else:
                missing.append({"name": name, "freq": s.get("freq", 0), "tier": tier_name})
        all_matched.extend(matched_list)
        practiced_count = sum(1 for m in matched_list if m["status"] in ("practiced", "completed"))
        claimed_count   = sum(1 for m in matched_list if m["status"] == "claimed")
        return {
            "total":           total,
            "matched":         len(matched_list),
            "pct":             int(len(matched_list) / total * 100) if total else 0,
            "practiced_count": practiced_count,
            "claimed_count":   claimed_count,
        }

    core_stats      = _process_tier(core,      "core")
    important_stats = _process_tier(important, "important")
    bonus_stats     = _process_tier(bonus,     "bonus")

    missing.sort(key=lambda x: x["freq"], reverse=True)

    # Sort matched skills: completed first, then practiced, then claimed; within same status by tier+freq
    _status_rank = {"completed": 3, "practiced": 2, "claimed": 1}
    _tier_rank   = {"core": 3, "important": 2, "bonus": 1}
    all_matched.sort(
        key=lambda x: (_status_rank.get(x["status"] or "", 0), _tier_rank.get(x["tier"], 0), x["freq"]),
        reverse=True,
    )

    # NOTE: 已删除 positioning / positioning_level —— 简历数据无法可信判断熟练度级别。
    # 前端改为展示事实陈述（覆盖率、项目实证数），不贴 senior/mid/junior 标签。

    return {
        "core":              core_stats,
        "important":         important_stats,
        "bonus":             bonus_stats,
        "top_missing":       missing[:8],
        "matched_skills":    all_matched[:12],
        "has_project_data":  has_project_data,
    }
