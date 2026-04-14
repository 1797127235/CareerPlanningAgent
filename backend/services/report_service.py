"""
Report service — generates career development reports.

Four-dimension scoring pipeline:
  基础要求  — education + experience match vs job requirements
  职业技能  — weighted skill-tier match (reuses growth_log formula)
  职业素养  — currently None (interview practice module removed)
  发展潜力  — readiness trend slope + project count + transition_probability

Data sources:
  Profile.profile_json        → skills, education, experience_years
  CareerGoal                  → target_node_id, gap_skills, transition_probability
  GrowthSnapshot[]            → readiness curve
  ProjectRecord[]             → completed projects
  data/graph.json             → skill_tiers, career_ceiling, soft_skills, career_alignment candidates
  data/market_signals.json    → demand_change_pct, salary_cagr, timing
  data/level_skills.json      → per-level skill lists (optional, for action plan)
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_USE_LLM_ACTION_PLAN = os.getenv("USE_LLM_ACTION_PLAN", "true").lower() == "true"

# Project root = two levels up from this file (backend/services/report_service.py)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"

# ── Static data (loaded once per process) ─────────────────────────────────────

_GRAPH_NODES: dict[str, dict] = {}
_LEVEL_SKILLS: dict[str, dict] = {}
_MARKET: dict[str, dict] = {}        # family_name → signal dict
_NODE_TO_FAMILY: dict[str, str] = {} # node_id → family_name

_SKILL_FILL_PATH_PATH = _PROJECT_ROOT / "data" / "skill_fill_path_tags.json"
_SKILL_FILL_PATH_CACHE: dict[str, str] | None = None


def _load_skill_fill_path_cache() -> dict[str, str]:
    global _SKILL_FILL_PATH_CACHE
    if _SKILL_FILL_PATH_CACHE is not None:
        return _SKILL_FILL_PATH_CACHE
    if not _SKILL_FILL_PATH_PATH.exists():
        _SKILL_FILL_PATH_CACHE = {}
        return _SKILL_FILL_PATH_CACHE
    try:
        data = json.loads(_SKILL_FILL_PATH_PATH.read_text(encoding="utf-8"))
        _SKILL_FILL_PATH_CACHE = {k: v for k, v in data.items() if v in {"learn", "practice", "both"}}
    except Exception as e:
        logger.warning("Failed to load skill_fill_path_tags.json: %s", e)
        _SKILL_FILL_PATH_CACHE = {}
    return _SKILL_FILL_PATH_CACHE


_LEARN_KEYWORDS = {
    "数据结构", "算法", "操作系统", "计算机网络", "计算机组成",
    "数据库原理", "编译原理", "离散数学", "概率", "线性代数",
    "设计模式", "计算机体系", "机器学习原理",
}
_PRACTICE_KEYWORDS = {
    "高并发", "分布式", "性能优化", "架构", "微服务",
    "消息队列", "中间件", "负载均衡", "系统设计",
    "容灾", "秒杀", "限流",
}
_BOTH_KEYWORDS = {
    "Docker", "Kubernetes", "K8s", "Git", "CI/CD",
    "单元测试", "集成测试", "Code Review", "Terraform",
    "Prometheus", "Grafana",
}

_PROJECT_SKILL_HINTS: dict[str, list[str]] = {
    "性能优化": ["性能", "高性能", "压测", "benchmark", "qps", "延迟", "吞吐", "profile", "热点", "优化"],
    "高并发":   ["并发", "高并发", "多线程", "线程池", "epoll", "reactor", "内存池", "qps", "压测"],
    "系统编程": ["系统编程", "系统调用", "内核", "epoll", "reactor", "内存池", "多线程", "linux系统", "io_uring"],
    "网络编程": ["网络", "socket", "tcp", "epoll", "reactor", "网络库", "网络框架"],
    "内存管理": ["内存", "内存池", "tcmalloc", "jemalloc", "malloc", "分配器"],
    "GDB":      ["gdb", "调试", "core dump", "断点"],
    "CMake":    ["cmake", "makefile", "构建", "编译系统"],
    "Linux":    ["linux", "系统调用", "epoll", "内核", "posix"],
    "STL":      ["stl", "标准库", "容器", "迭代器", "模板"],
    "多线程":   ["多线程", "线程池", "并发", "锁", "mutex", "原子操作"],
    "C++":      ["c++", "cpp", "stl", "模板", "虚函数"],
}


def _classify_fill_path(skill_name: str, covered_by_project: bool = False) -> str:
    cache = _load_skill_fill_path_cache()
    if skill_name in cache:
        return cache[skill_name]
    s = skill_name.lower()
    for kw in _LEARN_KEYWORDS:
        if kw.lower() in s:
            return "learn"
    for kw in _PRACTICE_KEYWORDS:
        if kw.lower() in s:
            return "practice"
    for kw in _BOTH_KEYWORDS:
        if kw.lower() in s:
            return "both"
    return "practice" if covered_by_project else "both"


# Career-alignment graph cache (auto-invalidates on mtime change)
_graph_cache: list[dict] | None = None
_graph_mtime: float = 0.0


def _load_graph_nodes() -> list[dict]:
    """Load & cache graph.json nodes, auto-invalidate on mtime change."""
    global _graph_cache, _graph_mtime
    try:
        graph_path = _DATA_DIR / "graph.json"
        mtime = graph_path.stat().st_mtime
        if _graph_cache is None or mtime != _graph_mtime:
            with open(graph_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            _graph_cache = data.get("nodes", [])
            _graph_mtime = mtime
        return _graph_cache or []
    except Exception as e:
        logger.warning("Failed to load graph.json: %s", e)
        return []


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
    # Project evidence takes priority: if the skill is demonstrated in projects,
    # it counts as matched even if the user didn't explicitly list it in skills.
    if has_project_data:
        if _skill_in_set(skill_name, completed_practiced):
            return True, "completed"
        if _skill_in_set(skill_name, practiced):
            return True, "practiced"

    if not _skill_matches(skill_name, user_skills):
        return False, None
    if not has_project_data:
        return True, "claimed"
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
                text = f"已有项目实践涉及 {name}，但描述中缺少系统性的知识梳理和可验证的技术文档，这在面试中容易被追问。"
            elif s["fill_path"] == "practice":
                text = f"已有项目涉及 {name} 方向，但缺少可量化的性能数据、测试覆盖说明或深度技术文档，难以在面试中体现工程深度。"
            else:
                text = f"已有项目涉及 {name} 方向，但缺少可量化的性能数据、测试覆盖说明或深度技术文档，这在面试中容易被追问。"
            tag = "具体盲区"
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


# ── Career alignment analysis ────────────────────────────────────────────────

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


def _build_alignment_prompt(skills, projects, soft_skills, candidates, target_node_id, profile_data=None):
    # 合并简历 + 成长档案项目
    all_projects = _normalize_project_sources(profile_data or {}, projects)

    proj_lines = []
    for p in all_projects[:8]:  # 最多 8 个项目，防 prompt 过长
        tag = "简历" if p["source"] == "resume" else "档案"
        proj_lines.append(f"- [{tag}] [{p['name']}] {p['desc'][:220]}")
    projects_block = "\n".join(proj_lines) or "（无项目数据）"

    # 软技能
    ss_lines = []
    for k, v in (soft_skills or {}).items():
        if k.startswith("_"):
            continue
        if isinstance(v, (int, float)):
            ss_lines.append(f"- {k}: {int(v)}/100")
    soft_block = "\n".join(ss_lines) or "（无软技能评估）"

    # 候选节点
    cand_lines = []
    for c in candidates:
        cand_lines.append(
            f'- {{"node_id": "{c["node_id"]}", '
            f'"label": "{c["label"]}", '
            f'"role_family": "{c.get("role_family", "")}", '
            f'"career_level": "{c.get("career_level", "")}", '
            f'"key_skills": {c["must_skills"][:5]}}}'
        )
    candidates_block = "\n".join(cand_lines)

    target_hint = ""
    if target_node_id:
        target_hint = f"\n\n学生目前标定的目标岗位 node_id: {target_node_id}（若此岗位在候选列表中，请给出对齐评估；若不在，请观察其他对齐方向）"

    return f"""你是职业数据分析师。你的任务是根据学生数据**观察 + 对齐**，不做预测、不贴级别、不给时间表。

# 严格规则

1. **只陈述事实**：所有结论必须能从给定的学生数据里找到依据
2. **不做时间预测**：禁止输出"N 年到 senior"这类时间表
3. **不贴等级标签**：禁止输出"你是中级/初级/资深"这类分类判断
4. **node_id 只能从候选列表里选**：不许自创岗位名、不许拼接新词
5. **每个 alignment 必须引用具体 evidence**：要么是学生某个项目里的数字、要么是某个技能名、要么是某个软技能分数——不许空泛描述
6. **不确定就说不知道**：把无法从数据里得出的结论放进 `cannot_judge` 字段
7. **最多输出 3 条 alignments**，按对齐度排序

# 学生数据

## 技能（来自简历 + 成长档案）
{", ".join(skills[:30])}

## 项目（含数据）
{projects_block}

## 软技能评估
{soft_block}
{target_hint}

# 候选岗位（你只能从这 {len(candidates)} 个里选）

{candidates_block}

# 输出 JSON schema（严格遵守，不要额外文字）

{{
  "observations": "2-3 句对学生数据的事实观察，必须引用具体数据",
  "alignments": [
    {{
      "node_id": "从候选列表里选的 node_id",
      "score": 0.85,
      "evidence": "引用学生具体项目/数字/技能作为对齐证据",
      "gap": "对齐到该岗位还差什么（可以为空字符串）"
    }}
  ],
  "cannot_judge": [
    "你无法从数据里判断的维度，例如：'实际工作节奏与晋升速度'"
  ]
}}

只输出 JSON，不要 markdown 代码块包裹，不要解释性文字。
"""


def _build_career_alignment(
    profile_data: dict,          # profile.profile_json 解析后的 dict
    projects: list,              # ProjectRecord list
    graph_nodes: list[dict],     # data/graph.json 的 nodes 数组
    target_node_id: str | None = None,  # 学生当前的目标岗位（如有）
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

    # ── [Step 2] 构造 Prompt ──
    prompt = _build_alignment_prompt(
        skills=skills,
        projects=projects,
        soft_skills=soft_skills,
        candidates=candidates,
        target_node_id=target_node_id,
        profile_data=profile_data,  # 让 prompt builder 也能读简历项目
    )

    # ── [Step 3] 调用 LLM ──
    parsed: dict | None = None
    try:
        from backend.llm import get_llm_client, get_model
        resp = get_llm_client(timeout=120).chat.completions.create(
            model=get_model("slow"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1200,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw.strip())
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


# ── LLM narrative generator ───────────────────────────────────────────────────

_NARRATIVE_SYSTEM = """你是一位兼具数据敏感度和教练视角的职业规划顾问，正在为一名IT学生撰写职业发展报告的核心评估段落。
要求：
- 语言亲切专业，直接称呼"你"，200-300字
- 结合具体数据说话（技能匹配、分数、差距）
- 指出最大亮点和最需改进的1-2个方向
- 适当体现"职业阶段感"：如果是初级方向强调基础与完整度，如果是中高级方向强调系统深度与可量化影响
- 如果项目描述缺少"动词+动作+数字"的 impact-first 结构，要把它作为简历层面的关键观察点提出来
- 结尾给出一句鼓励性总结，并传递一种温和的"计划性偶发"（Planned Happenstance）态度：职业路径往往是非线性的，保持好奇心和小步尝试比追求完美规划更重要
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

        # Projects context（含描述，让 LLM 能基于真实项目推理而不是空谈）
        proj_text = ""
        if projects:
            proj_lines = []
            for p in projects[:4]:
                name = getattr(p, "name", "") or "未命名"
                desc = getattr(p, "description", "") or getattr(p, "_desc", "") or ""
                status = getattr(p, "status", "")
                status_tag = "[已完成]" if status == "completed" else "[进行中]" if status == "in_progress" else ""
                if desc:
                    proj_lines.append(f"{status_tag}{name}：{desc[:180]}")
                else:
                    proj_lines.append(f"{status_tag}{name}")
            proj_text = "\n".join(proj_lines)

        # Claimed-but-unverified skills (risk signal)
        # 注：经 6b embedding + 6c LLM 隐式推断之后仍未匹配到项目的，才算真 claimed
        claimed_text = ""
        if claimed_skills:
            claimed_text = (
                f"简历声称但无项目可对应的技能：{', '.join(claimed_skills[:3])}。"
                "⚠️ 仅当该技能确实无法从现有项目推理出使用场景时，才当作面试风险点；"
                "如果学生的项目隐式使用了这些技能（例如 C++ 后端项目必然用 STL），不要当成风险。"
            )

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

        # Resume impact-first observation
        resume_impact_text = ""
        if projects:
            has_metrics = any(
                any(d in (getattr(p, "description", "") + getattr(p, "_desc", "")).lower() for d in ["qps", "latency", "用户", "日活", "准确率", "提升", "%", "倍", "ms", "tps"])
                for p in projects[:4]
            )
            if not has_metrics:
                resume_impact_text = "注意：该学生项目描述中缺少可量化的结果数字（如 QPS、用户数、准确率等），这意味着简历可能还停留在'做了什么'而不是'做成了什么'的层面。"

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
{resume_impact_text}

要求：
- 语言亲切专业，直接称呼"你"
- **不要罗列分数**（例如"职业技能维度得分 47，发展潜力 50"这类 X 分 Y 分的堆砌）。分数已经在页面其他地方展示，你的文字要讲**故事**，不要复读数据
- 必须引用学生项目里的具体细节（项目名 + 做法或数字）作为推理依据，**严禁泛泛而谈**
- 点名最大优势和最需改进的 1-2 个方向时，每条结论都要能回指上面的项目或数字
- 对"简历声称但无项目可对应的技能"要先判断：该技能是否已经**隐式用在学生现有项目里**？
  • 如果是（例如做 C++ 网络库必然用到 STL+Linux socket），**不要**列为面试风险
  • 只有确实找不到任何项目能证明的技能，才能提风险
- 如果项目缺少量化数字，要把"缺少 impact-first 叙事"当作一个独立的简历观察点提出来
- 严禁输出"建议聚焦实战项目填补技能缺口"、"保持当前成长势头"、"持续积累实战项目经验"、"相信你一定行"这类万能套话
- 结尾一句鼓励，要具体（例如"把下一个 demo 的 QPS 数据写进档案就能封堵这个缺口"这种），并传递职业路径可以是非线性的、小步尝试同样有价值的温和态度
- 直接输出段落，不要标题"""

        # 带重试：首次 60s 超时，失败再试一次 90s；max_tokens 收敛到 400 降低耗时
        client = get_llm_client(timeout=60)
        last_err: Exception | None = None
        for attempt in range(2):
            try:
                resp = client.chat.completions.create(
                    model=get_model("fast"),
                    messages=[
                        {"role": "system", "content": _NARRATIVE_SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.5,
                    max_tokens=400,
                )
                return resp.choices[0].message.content.strip()
            except Exception as inner:
                last_err = inner
                logger.warning("Narrative attempt %d failed: %s", attempt + 1, inner)
                if attempt == 0:
                    # 第二次用更长超时 + 更短 max_tokens
                    client = get_llm_client(timeout=90)
        if last_err:
            raise last_err

    except Exception as e:
        # 重试两次都失败——诚实告知，不伪装 AI 输出
        logger.error("Narrative generation FAILED after retries: %s", e, exc_info=True)
        err_type = type(e).__name__
        err_msg = str(e)[:180] if str(e) else err_type
        return (
            f"⚠️ AI 综合评价暂时生成失败（{err_type}）。"
            f"这通常是大模型调用超时、配额或网络问题造成的——报告其他部分不受影响，"
            f"可稍后点击右上角「AI 润色」按钮重试综合评价。"
            f"\n\n[诊断信息：{err_msg}]"
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

    # Smart project-name extraction (same logic as generate_report's _short_proj_name)
    def _smart_name(desc: str) -> str:
        before_punct = _re_diag.split(r'[，。,.、；]', desc)[0].strip()
        m = _re_diag.search(r'实现(?:了|的)?\s*(.{4,20}?)$', before_punct)
        if m:
            candidate = m.group(1).strip()
            candidate = _re_diag.sub(r'^[的了地一个款]{1,3}', '', candidate).strip()
            if len(candidate) >= 4:
                return candidate
        m2 = _re_diag.search(r'的\s*((?:[A-Za-z+#]+\s*)?[\u4e00-\u9fff]{2,}[\u4e00-\u9fff\w+# ]*)$', before_punct)
        if m2:
            candidate = m2.group(1).strip()
            if 4 <= len(candidate) <= 20:
                return candidate
        raw = before_punct[:30].strip() if len(before_punct) > 30 else before_punct
        return _re_diag.sub(r'^[的了地是]{1,2}\s*', '', raw).strip()

    # Resume-extracted projects
    raw_projects = profile_data.get("projects", [])
    for i, p in enumerate(raw_projects):
        if isinstance(p, str) and p.strip():
            items_to_check.append({"name": _smart_name(p), "text": p, "source_type": "resume", "source_id": i})
        elif isinstance(p, dict):
            name = p.get("name", "")
            desc = p.get("description", "") or name
            if desc:
                items_to_check.append({"name": name or _smart_name(desc), "text": desc, "source_type": "resume", "source_id": i})

    # Growth log projects
    for p in (projects or []):
        desc = getattr(p, "description", "") or ""
        name = getattr(p, "name", "") or ""
        text = desc if desc else name
        if text and not any(i["text"] == text for i in items_to_check):
            items_to_check.append({"name": name or _smart_name(text), "text": text, "source_type": "growth_log", "source_id": getattr(p, "id", 0)})

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
            "source_type": item["source_type"],
            "source_id": item["source_id"],
            "current_text": item["text"],
            "status": "needs_improvement",
            "highlight": s.get("highlight", ""),
            "issues": item["issues"],
            "suggestion": s.get("suggestion", ""),
        })

    for item in passed:
        results.append({
            "source": item["name"],
            "source_type": item["source_type"],
            "source_id": item["source_id"],
            "current_text": item["text"],
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
            _infer_resp = get_llm_client(timeout=60).chat.completions.create(
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

        # 6c. LLM 隐式技能推断 pre-pass：
        #     embedding 只能捕捉语义相似度，无法推理"C++ 网络库必然用 STL+Linux"
        #     这种技术栈依赖关系。让 LLM 读项目描述，显式推断隐式用到的技术。
        _still_uncovered = [
            s for s in _user_skills_all
            if not _skill_in_set(s, practiced)
        ]
        if _still_uncovered and profile_proj_descs:
            _llm_implicit = _infer_implicit_skills_llm(
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
        if _skill_matches(_req_skill, _user_skills_all) or _skill_in_set(_req_skill, practiced):
            continue
        _hints = _PROJECT_SKILL_HINTS.get(_req_skill, [])
        if any(_h in _all_project_text for _h in _hints):
            practiced.add(_req_skill.lower().strip())

    # 7. Compute four dimensions
    foundation_score = _score_foundation(profile_data, node)
    skills_score = _score_skills(profile_data, node, practiced, completed_practiced)
    qualities_score = None
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

    # ── Action plan ───────────────────────────────────────────────────────────
    if _USE_LLM_ACTION_PLAN:
        try:
            from backend.services.action_plan_llm import build_action_plan_with_llm
            _plan_context = {
                "node_label": goal.target_label,
                "ai_impact_narrative": node.get("ai_impact_narrative", ""),
                "differentiation_advice": node.get("differentiation_advice", ""),
                "skills": list(_user_skills_all),
                "projects": [
                    {"name": pp.get("name", ""), "desc": pp.get("desc", "")}
                    for pp in profile_proj_descs
                ],
                "app_count": len(applications or []),
                "top_missing": skill_gap.get("top_missing", []) if skill_gap else [],
                "market": {
                    "demand_change_pct": market_info.get("demand_change_pct") if market_info else None,
                    "salary_cagr": market_info.get("salary_cagr") if market_info else None,
                    "salary_p50": node.get("salary_p50", 0),
                },
            }
            action_plan = build_action_plan_with_llm(_plan_context)
        except Exception as e:
            logger.warning("LLM action plan failed, falling back to template: %s", e)
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
                profile_proj_descs=profile_proj_descs,
            )
    else:
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
            profile_proj_descs=profile_proj_descs,
        )

    # 10. LLM narrative — 用合并后的 projects（成长档案 + 简历项目），
    #     防止成长档案为空时 narrative 缺项目素材只能输出套话
    narrative = _generate_narrative(
        target_label=goal.target_label,
        match_score=match_score,
        four_dim=four_dim,
        gap_skills=goal.gap_skills or [],
        market_info=market_info,
        growth_delta=growth_delta,
        education=profile_data.get("education"),
        projects=merged_projects,   # ← 关键修复：从 projects 改成 merged_projects
        claimed_skills=claimed_skills[:3],
        applications=applications,
    )

    # 10b. Profile diagnosis (档案体检 — content completeness check)
    diagnosis = _diagnose_profile(
        profile_data=profile_data,
        projects=projects,
        node_label=goal.target_label,
    )

    # ── 方向对齐分析（LLM 分析 + graph 绑定）──
    try:
        career_alignment = _build_career_alignment(
            profile_data=profile_data,
            projects=projects,
            graph_nodes=_load_graph_nodes(),
            target_node_id=node_id,
        )
    except Exception as e:
        logger.warning("Career alignment build failed: %s", e)
        # 硬兜底：绝不返回 None，避免前端显示「数据不足」写死 UI
        career_alignment = {
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

    # 12. Build enriched project recommendations + skill fill path map
    import copy
    project_recs_raw = node.get("project_recommendations", [])[:3]
    top_missing_raw = skill_gap.get("top_missing", []) if skill_gap else []

    enriched_projects, enriched_missing, project_mismatch = _build_skill_fill_path_map(
        project_recs_raw, top_missing_raw
    )

    report_skill_gap = copy.deepcopy(skill_gap) if skill_gap else None
    if report_skill_gap is not None:
        report_skill_gap["top_missing"] = enriched_missing

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
        "narrative": narrative,
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
        "action_plan": action_plan,
        "delta": delta,
        "soft_skills": node.get("soft_skills", {}),
        "career_alignment": career_alignment,
        "differentiation_advice": node.get("differentiation_advice", ""),
        "ai_impact_narrative": node.get("ai_impact_narrative", ""),
        "project_recommendations": enriched_projects,
        "project_mismatch": project_mismatch,
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
