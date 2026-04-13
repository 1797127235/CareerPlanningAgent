"""
Report service — generates career development reports.

Four-dimension scoring pipeline:
  基础要求  — education + experience match vs job requirements
  职业技能  — weighted skill-tier match (reuses growth_log formula)
  职业素养  — mock interview dimension averages (None if no data)
  发展潜力  — readiness trend slope + project count + transition_probability

Data sources:
  Profile.profile_json        → skills, education, experience_years
  CareerGoal                  → target_node_id, gap_skills, transition_probability
  GrowthSnapshot[]            → readiness curve
  MockInterviewSession[]      → interview dimension scores
  ProjectRecord[]             → completed projects
  data/graph.json             → promotion_path, skill_tiers, career_ceiling, etc.
  data/market_signals.json    → demand_change_pct, salary_cagr, timing
  data/level_skills.json      → per-level skill lists (optional, for action plan)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Project root = two levels up from this file (backend/services/report_service.py)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"

# ── Static data (loaded once per process) ─────────────────────────────────────

_GRAPH_NODES: dict[str, dict] = {}
_LEVEL_SKILLS: dict[str, dict] = {}
_MARKET: dict[str, dict] = {}        # family_name → signal dict
_NODE_TO_FAMILY: dict[str, str] = {} # node_id → family_name


def reload_static() -> None:
    """Force-reload all static data (call after regenerating data files)."""
    global _GRAPH_NODES, _LEVEL_SKILLS, _MARKET, _NODE_TO_FAMILY
    _GRAPH_NODES = {}
    _LEVEL_SKILLS = {}
    _MARKET = {}
    _NODE_TO_FAMILY = {}
    _load_static()


def _load_static() -> None:
    global _GRAPH_NODES, _LEVEL_SKILLS, _MARKET, _NODE_TO_FAMILY
    if _GRAPH_NODES:
        return

    try:
        raw = json.loads((_DATA_DIR / "graph.json").read_text(encoding="utf-8"))
        _GRAPH_NODES = {n["node_id"]: n for n in raw.get("nodes", [])}
    except Exception as e:
        logger.warning("graph.json load failed: %s", e)

    try:
        _LEVEL_SKILLS = json.loads((_DATA_DIR / "level_skills.json").read_text(encoding="utf-8"))
    except Exception:
        pass  # optional — fallback to gap_skills

    try:
        raw_market = json.loads((_DATA_DIR / "market_signals.json").read_text(encoding="utf-8"))
        _MARKET = raw_market if isinstance(raw_market, dict) else {}
        for family, info in _MARKET.items():
            for nid in info.get("node_ids", []):
                _NODE_TO_FAMILY[nid] = family
        # Fallback: nodes missing from market_signals → alias to nearest family
        _FAMILY_ALIASES = {
            "systems-cpp": "cpp",   # 系统C++归属系统编程族
        }
        for node, alias in _FAMILY_ALIASES.items():
            if node not in _NODE_TO_FAMILY and alias in _NODE_TO_FAMILY:
                _NODE_TO_FAMILY[node] = _NODE_TO_FAMILY[alias]
    except Exception as e:
        logger.warning("market_signals.json load failed: %s", e)


# ── Helpers ───────────────────────────────────────────────────────────────────

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


def _user_skill_set(profile_data: dict) -> set[str]:
    raw = profile_data.get("skills", [])
    if not raw:
        return set()
    if isinstance(raw[0], dict):
        return {s.get("name", "").lower().strip() for s in raw if s.get("name")}
    return {s.lower().strip() for s in raw if isinstance(s, str) and s.strip()}


def _norm_skill(s: str) -> str:
    return s.lower().strip().replace(" ", "").replace("-", "").replace("_", "")


def _skill_matches(skill_name: str, user_skills: set[str]) -> bool:
    """Reuse same matching logic as growth_log_service."""
    name = skill_name.lower().strip()
    name_norm = _norm_skill(skill_name)
    if not name:
        return False
    if name in user_skills:
        return True
    if len(name_norm) <= 2:
        return False
    for us in user_skills:
        if not us:
            continue
        us_norm = _norm_skill(us)
        if name_norm == us_norm:
            return True
        if len(us_norm) > 2 and (name_norm in us_norm or us_norm in name_norm):
            return True
    return False


def _skill_in_set(skill_name: str, skill_set: set[str]) -> bool:
    """Fuzzy-check whether skill_name appears in a given set (e.g. practiced skills from projects)."""
    if not skill_set:
        return False
    name_norm = _norm_skill(skill_name)
    if not name_norm:
        return False
    for s in skill_set:
        s_norm = _norm_skill(s)
        if name_norm == s_norm:
            return True
        if len(name_norm) > 2 and len(s_norm) > 2 and (name_norm in s_norm or s_norm in name_norm):
            return True
    return False


def _skill_proficiency(
    skill_name: str,
    user_skills: set[str],
    practiced: set[str],
    completed_practiced: set[str],
    has_project_data: bool,
) -> tuple[bool, str | None]:
    """
    Returns (is_matched, status):
      status = 'completed'  — used in a completed project (weight 1.2×)
             = 'practiced'  — used in any project (weight 1.0×)
             = 'claimed'    — resume only, not verified in projects (weight 0.7×)
             = None         — user doesn't have this skill
    When has_project_data is False (fresh student), matched skills get 'claimed'
    without the 0.7× penalty so new students aren't penalised.
    """
    if not _skill_matches(skill_name, user_skills):
        return False, None
    if not has_project_data:
        return True, "claimed"  # no project data → treat as claimed, no penalty
    if _skill_in_set(skill_name, completed_practiced):
        return True, "completed"
    if _skill_in_set(skill_name, practiced):
        return True, "practiced"
    return True, "claimed"


_PROFICIENCY_MULTIPLIER = {"completed": 1.2, "practiced": 1.0, "claimed": 0.7}


# ── Four-dimension scoring ─────────────────────────────────────────────────────

def _score_foundation(profile_data: dict, node: dict) -> int | None:
    """基础要求: education + experience match. Returns 0–100 or None."""
    scores = []

    # Education: check profile_json.education.major vs node.related_majors
    education = profile_data.get("education") or {}
    major = ""
    if isinstance(education, dict):
        major = (education.get("major") or "").lower().strip()
    elif isinstance(education, str):
        major = education.lower().strip()

    related_majors = [m.lower() for m in (node.get("related_majors") or [])]
    if major and related_majors:
        # Check if user major is in (or overlaps) the related majors
        is_match = any(major in rm or rm in major for rm in related_majors)
        scores.append(100 if is_match else 50)
    elif related_majors:
        # No major info → give neutral score
        scores.append(60)

    # Experience: compare profile_json.experience_years vs node.min_experience
    exp_years = profile_data.get("experience_years")
    min_exp = node.get("min_experience")
    if exp_years is not None and min_exp is not None:
        try:
            exp_f = float(exp_years)
            min_f = float(min_exp)
            if exp_f >= min_f:
                scores.append(100)
            elif min_f > 0:
                scores.append(max(0, int(exp_f / min_f * 100)))
            else:
                scores.append(100)
        except (TypeError, ValueError):
            pass

    if not scores:
        return None
    return int(sum(scores) / len(scores))


def _score_skills(
    profile_data: dict,
    node: dict,
    practiced: set[str] | None = None,
    completed_practiced: set[str] | None = None,
) -> int:
    """
    职业技能: weighted skill-tier match with three-tier proficiency multiplier.

    Multipliers (only applied when project data exists):
      completed project  → 1.2×  (实战完成)
      any project usage  → 1.0×  (项目使用)
      resume-only claim  → 0.7×  (仅简历声称)
      no project data    → 1.0×  (fallback, no penalty for fresh students)
    """
    user_skills = _user_skill_set(profile_data)
    practiced = practiced or set()
    completed_practiced = completed_practiced or set()
    has_project_data = bool(practiced or completed_practiced)

    tiers = node.get("skill_tiers") or {}
    core      = tiers.get("core")      or []
    important = tiers.get("important") or []
    bonus     = tiers.get("bonus")     or []

    tier_pairs = [(core, 1.0), (important, 0.6), (bonus, 0.3)]
    total_w = sum(len(t) * w for t, w in tier_pairs)
    if total_w == 0:
        return 0

    matched_w = 0.0
    for tier_list, base_w in tier_pairs:
        for e in tier_list:
            is_matched, status = _skill_proficiency(
                e.get("name", ""), user_skills, practiced, completed_practiced, has_project_data
            )
            if is_matched:
                multiplier = _PROFICIENCY_MULTIPLIER.get(status or "claimed", 1.0)
                matched_w += base_w * multiplier

    return min(100, int(matched_w / total_w * 100))


def _score_qualities(mock_sessions: list) -> int | None:
    """职业素养: average of interview dimension scores. None if no data."""
    if not mock_sessions:
        return None

    dim_scores: list[float] = []
    for session in mock_sessions:
        # Try mapped_dimensions first (structured per-dim scores)
        mapped_raw = getattr(session, "mapped_dimensions", None)
        if mapped_raw:
            try:
                dims = json.loads(mapped_raw)
                if isinstance(dims, dict):
                    for v in dims.values():
                        if isinstance(v, (int, float)) and 0 <= v <= 100:
                            dim_scores.append(float(v))
            except Exception:
                pass

        # Fallback: analysis_json overall rating → rough heuristic
        if not dim_scores:
            analysis_raw = getattr(session, "analysis_json", None)
            if analysis_raw:
                try:
                    analysis = json.loads(analysis_raw)
                    if isinstance(analysis, dict):
                        overall = analysis.get("overall", "")
                        strengths = analysis.get("strengths", [])
                        weaknesses = analysis.get("weaknesses", [])
                        if isinstance(strengths, list) and isinstance(weaknesses, list):
                            s_cnt = len(strengths)
                            w_cnt = len(weaknesses)
                            total = s_cnt + w_cnt
                            if total > 0:
                                dim_scores.append(s_cnt / total * 100)
                except Exception:
                    pass

    if not dim_scores:
        return None
    return min(100, int(sum(dim_scores) / len(dim_scores)))


def _score_potential(
    snapshots: list,
    projects: list,
    transition_probability: float,
) -> int:
    """发展潜力: readiness trend + completed projects + transition_probability."""
    scores: list[float] = []

    # 1. Readiness trend (slope across last 4+ snapshots)
    if len(snapshots) >= 2:
        recent = sorted(snapshots, key=lambda s: s.created_at)[-4:]
        values = [float(s.readiness_score) for s in recent]
        if len(values) >= 2:
            # Simple linear trend: compare first half avg vs second half avg
            mid = len(values) // 2
            avg_early = sum(values[:mid]) / mid
            avg_late = sum(values[mid:]) / (len(values) - mid)
            delta = avg_late - avg_early
            # delta > 0 → growing; normalize to 0-100
            trend_score = min(100, max(0, 50 + delta * 2))  # ±25 range maps to 0-100
            scores.append(trend_score)
    elif len(snapshots) == 1:
        scores.append(50.0)  # baseline — no trend data yet

    # 2. Completed projects (capped at 3 for scoring)
    # Only score if user has at least one project — otherwise 0 projects = no data, not a penalty
    if projects:
        completed_count = sum(1 for p in projects if getattr(p, "status", "") == "completed")
        project_score = min(100, completed_count * 33)
        scores.append(float(project_score))

    # 3. Transition probability from CareerGoal (already 0.0–1.0 or 0–100)
    if transition_probability:
        prob = transition_probability
        if prob <= 1.0:
            prob *= 100
        scores.append(min(100.0, float(prob)))

    if not scores:
        return 50  # fallback neutral score
    return int(sum(scores) / len(scores))


def _weighted_match_score(four_dim: dict) -> int:
    """Compute overall match score from four dimensions. Weights: skills=40%, potential=25%, foundation=20%, qualities=15%."""
    weights = {
        "skills": 0.40,
        "potential": 0.25,
        "foundation": 0.20,
        "qualities": 0.15,
    }
    total_w = 0.0
    total_score = 0.0
    for key, w in weights.items():
        val = four_dim.get(key)
        if val is not None:
            total_score += val * w
            total_w += w
    if total_w == 0:
        return 0
    return int(total_score / total_w)


# ── Skill gap analysis ────────────────────────────────────────────────────────

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
      positioning               — market positioning label (初级/中级/资深)
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

    # Market positioning based on core skill coverage
    core_pct   = core_stats["pct"]
    node_label = node.get("label", "工程师")
    if core_pct >= 80:
        positioning       = f"资深{node_label}"
        positioning_level = "senior"
    elif core_pct >= 50:
        positioning       = f"中级{node_label}"
        positioning_level = "mid"
    else:
        positioning       = f"初级{node_label}"
        positioning_level = "junior"

    return {
        "core":              core_stats,
        "important":         important_stats,
        "bonus":             bonus_stats,
        "top_missing":       missing[:8],
        "matched_skills":    all_matched[:12],
        "has_project_data":  has_project_data,
        "positioning":       positioning,
        "positioning_level": positioning_level,
    }


# ── Action plan builder ────────────────────────────────────────────────────────

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


def _cosine_sim(a: list[float], b: list[float]) -> float:
    """Pure-Python cosine similarity (no numpy dependency)."""
    import math
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _batch_embed(texts: list[str]) -> list[list[float]] | None:
    """
    Batch-embed a list of texts via DashScope text-embedding-v3.
    Returns list of embedding vectors, or None on failure.
    One API call for the whole batch — no per-text overhead.
    """
    if not texts:
        return []
    try:
        from backend.llm import get_llm_client
        client = get_llm_client(timeout=15)
        resp = client.embeddings.create(
            model="text-embedding-v3",
            input=texts,
        )
        # Preserve input order (API may reorder by index)
        ordered = sorted(resp.data, key=lambda d: d.index)
        return [d.embedding for d in ordered]
    except Exception as e:
        logger.warning("_batch_embed failed: %s", e)
        return None


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
) -> dict:
    """
    Build an action plan with three categories:
      - skills:   'validate' tasks for claimed-but-unverified skills FIRST,
                  then 'learn' tasks for missing skills
      - project:  concrete project suggestion referencing actual student projects
      - job_prep: resume / portfolio / application readiness tasks
    """
    user_skills = _user_skill_set(profile_data)
    has_projects = bool(projects) or bool(profile_data.get("projects"))

    # Project names for personalizing task text
    completed_proj_names = [p.name for p in (projects or []) if getattr(p, "status", "") == "completed"]
    any_proj_names = [p.name for p in (projects or [])]

    # ── Pre-classify missing skills via LLM (no hardcoded synonym tables) ──────
    # Collect all skill names that need classification (claimed + top_missing)
    # Preserve order; dedup without set scrambling
    _seen_names: set[str] = set()
    _all_skill_names: list[str] = []
    for _n in [*(claimed_skills or [])[:4], *(m.get("name", "") for m in top_missing[:6] if m.get("name"))]:
        if _n and _n not in _seen_names:
            _all_skill_names.append(_n)
            _seen_names.add(_n)
    _llm_coverage: dict[str, str | None] = _embed_classify_skills(
        _all_skill_names, projects or []
    ) if projects else {}

    # Find a relevant existing project to reference in tasks.
    # Priority: recorded (skills_used exact) > inferred (embedding) > none
    def _find_related_project(skill: str) -> tuple[str | None, str]:
        skill_norm = _norm_skill(skill)
        if not skill_norm:
            return None, "none"

        # 1. Highest confidence: skill explicitly in skills_used
        for p in (projects or []):
            for s in (p.skills_used or []):
                s_norm = _norm_skill(s)
                if s_norm and (skill_norm == s_norm or
                               (len(skill_norm) > 2 and (skill_norm in s_norm or s_norm in skill_norm))):
                    return p.name, "recorded"

        # 2. Embedding said this skill is covered by a project (semantic inference)
        for key, proj_name in _llm_coverage.items():
            if proj_name and _norm_skill(key) == skill_norm:
                return proj_name, "inferred"

        return None, "none"

    # ── 1. Skill tasks (from top_missing with JD freq, fallback to gap_skills) ──
    skill_tasks = []
    seen: set[str] = set()

    # ── Priority 1: Missing skills from real JD data ──
    # (Validate/claimed items removed — the skill gap section already shows "待验证" badges.
    #  Action plan items should drive real growth, not admin tasks like "add skill to log".)
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
            t["deliverable"] = "学习笔记录入成长档案"
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


# ── LLM narrative generator ───────────────────────────────────────────────────

_NARRATIVE_SYSTEM = """你是一位资深职业规划顾问，正在为一名IT学生撰写职业发展报告的核心评估段落。
要求：
- 语言亲切专业，200-300字
- 结合具体数据说话（技能匹配、分数、差距）
- 指出最大亮点和最需改进的1-2个方向
- 结尾给出一句鼓励性总结
- 直接输出段落文字，不要标题或标签"""


def _generate_narrative(
    target_label: str,
    match_score: int,
    four_dim: dict,
    gap_skills: list[str],
    market_info: dict | None,
    growth_delta: float,
    # Rich context for personalization
    education: dict | None = None,
    projects: list | None = None,
    claimed_skills: list[str] | None = None,
    applications: list | None = None,
) -> str:
    """Call LLM to generate personalized 200-300 char narrative using real student data."""
    try:
        from backend.llm import get_llm_client, get_model

        dim_labels = {"foundation": "基础要求", "skills": "职业技能",
                      "qualities": "职业素养", "potential": "发展潜力"}
        dim_text = []
        for k, label in dim_labels.items():
            v = four_dim.get(k)
            dim_text.append(f"- {label}: {v if v is not None else '暂无（需完成模拟面试）'}")

        # Education context
        edu_text = ""
        if education and isinstance(education, dict):
            school = education.get("school", "")
            major = education.get("major", "")
            if school or major:
                edu_text = f"学生背景：{school + ' ' if school else ''}{major + '专业' if major else ''}"

        # Projects context (names + key skills)
        proj_text = ""
        if projects:
            completed = [p for p in projects if getattr(p, "status", "") == "completed"]
            in_prog = [p for p in projects if getattr(p, "status", "") == "in_progress"]
            parts = []
            if completed:
                names = "、".join(p.name for p in completed[:3])
                parts.append(f"已完成项目：{names}")
            if in_prog:
                names = "、".join(p.name for p in in_prog[:2])
                parts.append(f"进行中：{names}")
            proj_text = "；".join(parts) if parts else ""

        # Claimed-but-unverified skills (risk signal)
        claimed_text = ""
        if claimed_skills:
            claimed_text = f"简历声称但成长档案无验证记录的技能：{', '.join(claimed_skills[:3])}（面试风险点）"

        # Application status
        apply_text = ""
        if applications:
            total = len(applications)
            active = [a for a in applications if getattr(a, "status", "") in ("applied", "screening", "scheduled", "interviewed")]
            apply_text = f"已投递 {total} 家公司，{len(active)} 个进行中"

        market_text = ""
        if market_info:
            market_text = (
                f"市场：该方向需求变化 {market_info.get('demand_change_pct', 0):+.0f}%，"
                f"入场时机{market_info.get('timing_label', '良好')}"
            )

        gap_text = "、".join(gap_skills[:4]) if gap_skills else "暂无明显差距"

        context_parts = [p for p in [edu_text, proj_text, claimed_text, apply_text] if p]
        context_block = "\n".join(context_parts) if context_parts else ""

        prompt = f"""为以下学生撰写职业发展报告的综合评价段落（200-300字）：

目标岗位：{target_label}
综合匹配分：{match_score}/100
近期成长趋势：{growth_delta:+.1f}分

四维评分：
{chr(10).join(dim_text)}

核心技能差距：{gap_text}
{market_text}

【学生真实档案】
{context_block if context_block else '（学生尚未完善档案）'}

要求：
- 语言亲切专业，直接称呼"你"
- 结合学生真实档案数据，不要说空话
- 点名最大优势和最需改进的1-2个方向
- 如有声称但未验证的技能，需提醒面试风险
- 结尾一句鼓励性话语
- 直接输出段落，不要标题"""

        client = get_llm_client(timeout=30)
        resp = client.chat.completions.create(
            model=get_model("fast"),
            messages=[
                {"role": "system", "content": _NARRATIVE_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=500,
        )
        return resp.choices[0].message.content.strip()

    except Exception as e:
        logger.warning("Narrative generation failed: %s", e)
        dim_s = four_dim.get("skills", 0)
        dim_p = four_dim.get("potential", 0)
        return (
            f"你在{target_label}方向的综合匹配度为 {match_score} 分，"
            f"职业技能维度得分 {dim_s}，发展潜力 {dim_p}。"
            f"{'核心差距技能：' + '、'.join(gap_skills[:3]) + '。' if gap_skills else ''}"
            f"建议聚焦提升技术深度，保持当前成长势头，持续积累实战项目经验。"
        )


# ── Profile diagnosis (档案体检) ─────────────────────────────────────────────

import re as _re_diag

_HOLLOW_PATTERNS = [
    {
        "id": "no_numbers",
        "detect": lambda text: not _re_diag.search(r'\d', text),
        "label": "缺少量化数据",
    },
    {
        "id": "no_result",
        "detect": lambda text: not any(w in text for w in [
            '提升', '降低', '优化', '减少', '增加', '支撑', '处理',
            '完成', 'QPS', 'TPS', '延迟', '吞吐', '并发', '覆盖率',
            'improve', 'reduce', 'increase', 'optimize',
        ]),
        "label": "缺少成果描述",
    },
    {
        "id": "too_short",
        "detect": lambda text: len(text.strip()) < 30,
        "label": "描述过于简短",
    },
    {
        "id": "vague_participation",
        "detect": lambda text: '参与' in text and '负责' not in text and '实现' not in text and '开发' not in text,
        "label": "只说参与未说明职责",
    },
]


def _diagnose_profile(
    profile_data: dict,
    projects: list,
    node_label: str,
) -> list[dict]:
    """
    Scan profile projects/experience for hollow statements.
    Returns list of diagnosis items, each with:
      - source: project name or "简历"
      - status: "pass" | "needs_improvement"
      - highlight: what's good (亮点)
      - issues: list of detected problems
      - suggestion: specific text to add (from LLM)
    """
    # Collect all describable items: resume projects + growth log projects
    items_to_check: list[dict] = []

    # Resume-extracted projects
    raw_projects = profile_data.get("projects", [])
    for p in raw_projects:
        if isinstance(p, str) and p.strip():
            items_to_check.append({"name": p[:20], "text": p, "source": "resume"})
        elif isinstance(p, dict):
            name = p.get("name", "")
            desc = p.get("description", "") or name
            if desc:
                items_to_check.append({"name": name or desc[:20], "text": desc, "source": "resume"})

    # Growth log projects
    for p in (projects or []):
        desc = getattr(p, "description", "") or ""
        name = getattr(p, "name", "") or ""
        text = desc if desc else name
        if text and not any(i["text"] == text for i in items_to_check):
            items_to_check.append({"name": name or text[:20], "text": text, "source": "growth_log"})

    if not items_to_check:
        return []

    # Step 1: Rule-based detection
    needs_fix: list[dict] = []
    passed: list[dict] = []

    for item in items_to_check:
        text = item["text"]
        issues = [p["label"] for p in _HOLLOW_PATTERNS if p["detect"](text)]
        if issues:
            needs_fix.append({**item, "issues": issues})
        else:
            passed.append(item)

    # Step 2: LLM generates specific suggestions for items with issues
    suggestions: dict[str, dict] = {}  # name -> {highlight, suggestion}
    if needs_fix:
        try:
            from backend.llm import get_llm_client, get_model

            items_text = "\n".join(
                f"- 项目「{it['name']}」: {it['text'][:100]}\n  问题: {', '.join(it['issues'])}"
                for it in needs_fix
            )

            prompt = f"""你是简历优化专家。学生目标岗位是「{node_label}」。

以下项目/经历存在描述问题，请为每个项目输出：
1. highlight: 一句话总结亮点（肯定学生做了什么）
2. suggestion: 具体建议补充的文字（包含具体数字占位符如 XX，让学生填入真实数据）

{items_text}

输出 JSON 数组，每项包含 name、highlight、suggestion。只输出 JSON。"""

            resp = get_llm_client(timeout=20).chat.completions.create(
                model=get_model("fast"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=800,
            )
            raw = resp.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            parsed = json.loads(raw.strip())
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and item.get("name"):
                        suggestions[item["name"]] = {
                            "highlight": item.get("highlight", ""),
                            "suggestion": item.get("suggestion", ""),
                        }
        except Exception as e:
            logger.warning("Profile diagnosis LLM failed: %s", e)

    # Step 3: Assemble results
    results: list[dict] = []

    for item in needs_fix:
        s = suggestions.get(item["name"], {})
        results.append({
            "source": item["name"],
            "status": "needs_improvement",
            "highlight": s.get("highlight", ""),
            "issues": item["issues"],
            "suggestion": s.get("suggestion", ""),
        })

    for item in passed:
        results.append({
            "source": item["name"],
            "status": "pass",
            "highlight": "",
            "issues": [],
            "suggestion": "",
        })

    return results


# ── Main report generator ─────────────────────────────────────────────────────

def generate_report(user_id: int, db) -> dict:
    """
    Generate a complete career development report for the current user.

    Returns the report data dict (to be serialized into Report.data_json).
    Raises ValueError if prerequisite data is missing.
    """
    # Always reload level_skills so changes from enrich scripts are picked up
    # without requiring a full server restart.
    global _LEVEL_SKILLS
    try:
        _LEVEL_SKILLS = json.loads((_DATA_DIR / "level_skills.json").read_text(encoding="utf-8"))
    except Exception:
        pass
    _load_static()

    from backend.db_models import (
        Profile, CareerGoal, GrowthSnapshot,
        MockInterviewSession, ProjectRecord,
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
    node = _GRAPH_NODES.get(node_id)
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

    # 4. Load mock interview sessions
    mock_sessions = (
        db.query(MockInterviewSession)
        .filter(
            MockInterviewSession.profile_id == profile.id,
            MockInterviewSession.status == "finished",
        )
        .order_by(MockInterviewSession.created_at.desc())
        .limit(5)
        .all()
    )

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
        m = _re.search(r'实现(?:了|的)?\s*(.{4,20}?)$', before_punct)
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

    # 5c. Rule-based skill extraction from description text.
    #     Scan each description for the user's own resume skills — if a skill name
    #     appears in the description text, it is considered "practiced" (no LLM needed,
    #     no timeout risk). LLM is used as an optional enrichment afterward.
    user_skills_raw = _user_skill_set(profile_data)  # normalized lowercase set

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
        desc_norm = _norm_skill(desc)
        for skill in user_skills_raw:
            if _matches_in_text(_norm_skill(skill), desc_norm):
                _desc_practiced.add(skill)  # keep original casing from user_skills_raw

    # Also scan growth log project names/descriptions
    for p in projects:
        if p.name:
            pname_norm = _norm_skill(p.name)
            for skill in user_skills_raw:
                if _matches_in_text(_norm_skill(skill), pname_norm):
                    _desc_practiced.add(skill)

    logger.info("Rule-based desc scan: found practiced skills %s", _desc_practiced)

    # Optional LLM enrichment for skills NOT in user's resume (e.g. Reactor, epoll)
    _inferred_skills_from_text: list[str] = list(_desc_practiced)
    _texts_to_infer = profile_projects_raw[:4] + [p.name for p in projects if not p.skills_used and p.name]
    if _texts_to_infer:
        try:
            from backend.llm import get_llm_client, get_model as _get_model
            _proj_list = "\n".join(f"- {t[:100]}" for t in _texts_to_infer)
            _infer_resp = get_llm_client(timeout=15).chat.completions.create(
                model=_get_model("fast"),
                messages=[{"role": "user", "content":
                    "以下项目描述，提取技术技能（3-8个，JSON数组，不要解释）：\n" + _proj_list}],
                temperature=0.1, max_tokens=300,
            )
            _raw = _infer_resp.choices[0].message.content.strip()
            if _raw.startswith("```"):
                _raw = _raw.split("```")[1]
                if _raw.startswith("json"):
                    _raw = _raw[4:]
            _extra = json.loads(_raw.strip())
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
    _user_skills_all = list(_user_skill_set(profile_data))
    _uncovered = [s for s in _user_skills_all if not _skill_in_set(s, practiced)]
    if _uncovered and profile_proj_descs:
        # Build lightweight proxy objects for profile descriptions
        class _EarlyProj:
            def __init__(self, name: str, desc: str):
                self.name = name
                self.skills_used: list[str] = []
                self._desc = desc
        _early_proj_objs = [_EarlyProj(pp["name"], pp["desc"]) for pp in profile_proj_descs]
        _early_proj_objs += [p for p in projects if getattr(p, "skills_used", None)]
        _embed_pre = _embed_classify_skills(_uncovered, _early_proj_objs)
        for _sk, _pj in _embed_pre.items():
            if _pj is not None:
                practiced.add(_sk.lower().strip())
        logger.info("Embedding pre-pass practiced additions: %s",
                    [k for k, v in _embed_pre.items() if v])

    # 7. Compute four dimensions
    foundation_score = _score_foundation(profile_data, node)
    skills_score = _score_skills(profile_data, node, practiced, completed_practiced)
    qualities_score = _score_qualities(mock_sessions)
    potential_score = _score_potential(
        snapshots, projects, float(goal.transition_probability or 0)
    )

    four_dim = {
        "foundation": foundation_score,
        "skills": skills_score,
        "qualities": qualities_score,
        "potential": potential_score,
    }
    match_score = _weighted_match_score(four_dim)

    # 7. Market signals
    family_name = _NODE_TO_FAMILY.get(node_id)
    market_info: dict | None = _MARKET.get(family_name) if family_name else None

    # 8. Skill gap analysis
    skill_gap = _build_skill_gap(profile_data, node, practiced, completed_practiced)

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
    if skill_gap:
        for m in skill_gap.get("matched_skills", []):
            if m.get("status") == "claimed" and m.get("tier") in ("core", "important"):
                claimed_skills.append(m["name"])

    # 9. Action plan — merge ProjectRecord list with profile_proj_descs so the action
    #    plan can reference profile project names even when growth log is empty.
    #    We create lightweight proxy objects that quack like ProjectRecord.
    class _ProfileProj:
        """Minimal proxy so profile_json projects look like ProjectRecord to action plan."""
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

    action_plan = _build_action_plan(
        gap_skills=goal.gap_skills or [],
        top_missing=skill_gap.get("top_missing", []) if skill_gap else [],
        node_id=node_id,
        node_label=goal.target_label,
        profile_data=profile_data,
        current_readiness=current_readiness,
        claimed_skills=claimed_skills,
        projects=merged_projects,
        applications=applications,
    )

    # 10. LLM narrative (now uses real student context)
    narrative = _generate_narrative(
        target_label=goal.target_label,
        match_score=match_score,
        four_dim=four_dim,
        gap_skills=goal.gap_skills or [],
        market_info=market_info,
        growth_delta=growth_delta,
        education=profile_data.get("education"),
        projects=projects,
        claimed_skills=claimed_skills[:3],
        applications=applications,
    )

    # 10b. Profile diagnosis (档案体检 — content completeness check)
    diagnosis = _diagnose_profile(
        profile_data=profile_data,
        projects=projects,
        node_label=goal.target_label,
    )

    # 11. Delta vs previous report
    delta = None
    from backend.db_models import Report
    prev_report = (
        db.query(Report)
        .filter(Report.user_id == user_id)
        .order_by(Report.created_at.desc())
        .first()
    )
    if prev_report:
        prev_data = _parse_data(prev_report.data_json)
        prev_score = prev_data.get("match_score", 0)
        prev_skills_matched = set()
        for m in (prev_data.get("skill_gap", {}).get("matched_skills", [])):
            prev_skills_matched.add(m.get("name", "").lower())

        new_skills_matched = set()
        for m in (skill_gap.get("matched_skills", [])):
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
        stages = action_plan.get("stages", [])
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
            pending_improvements = [s["name"] for s in skill_gap.get("top_missing", [])[:3]]

        delta = {
            "prev_score": prev_score,
            "score_change": match_score - prev_score,
            "prev_date": prev_report.created_at.isoformat() if prev_report.created_at else "",
            "gained_skills": gained_skills[:5],
            "still_missing": pending_improvements,
            "plan_progress": plan_progress,
            "next_action": next_action,
        }

    # 12. Assemble report payload
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
        "narrative": narrative,
        "diagnosis": diagnosis,
        "market": {
            "demand_change_pct": market_info.get("demand_change_pct", 0) if market_info else None,
            "salary_cagr": market_info.get("salary_cagr", 0) if market_info else None,
            "salary_p50": node.get("salary_p50", 0),
            "timing": market_info.get("timing", "good") if market_info else "good",
            "timing_label": market_info.get("timing_label", "") if market_info else "",
        },
        "skill_gap": skill_gap,
        "growth_curve": growth_curve,
        "action_plan": action_plan,
        "delta": delta,
        "promotion_path": node.get("promotion_path", []),
        "soft_skills": node.get("soft_skills", {}),
        "positioning": skill_gap.get("positioning", "") if skill_gap else "",
        "positioning_level": skill_gap.get("positioning_level", "junior") if skill_gap else "junior",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    return report_data


# ── Polish (AI润色) ────────────────────────────────────────────────────────────

def polish_narrative(narrative: str, target_label: str) -> str:
    """Re-polish an existing narrative via LLM."""
    try:
        from backend.llm import get_llm_client, get_model

        prompt = f"""以下是一段针对「{target_label}」职业方向的发展报告评价段落，请在保留核心信息的前提下进行润色优化：
- 语言更流畅、专业
- 保持200-300字
- 保留所有具体数据
- 结尾保持鼓励性语气

原文：
{narrative}

请直接输出润色后的段落，不需要任何解释。"""

        client = get_llm_client(timeout=30)
        resp = client.chat.completions.create(
            model=get_model("fast"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=600,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("Polish failed: %s", e)
        return narrative
