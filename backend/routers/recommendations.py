"""Recommendations router — gap analysis only (LLM-based).

Old token-matching recommendation endpoints have been removed.
Role matching is now done via LLM in profiles._llm_match_role.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import get_db
from backend.db_models import CareerGoal, Profile, User

logger = logging.getLogger(__name__)

router = APIRouter()

_gap_cache: dict = {}

# ── Gap analysis DB cache helpers ─────────────────────────────────────────

def _load_gap_cache(profile: Profile, p_hash: str, role_id: str) -> dict | None:
    """Load cached gap analysis from DB for a specific role."""
    try:
        cached = json.loads(profile.cached_gaps_json or "{}")
    except (json.JSONDecodeError, TypeError):
        return None
    if cached.get("hash") != p_hash:
        return None
    return cached.get("roles", {}).get(role_id)


def _save_gap_cache(profile: Profile, p_hash: str, role_id: str, result: dict, db: Session):
    """Persist gap analysis result to DB."""
    try:
        cached = json.loads(profile.cached_gaps_json or "{}")
    except (json.JSONDecodeError, TypeError):
        cached = {}
    if cached.get("hash") != p_hash:
        cached = {"hash": p_hash, "roles": {}}
    cached.setdefault("roles", {})[role_id] = result
    profile.cached_gaps_json = json.dumps(cached, ensure_ascii=False)
    db.commit()

# ── Role data loader (replaces SkillMatchService for role lookup) ─────────

_roles_data: dict[str, dict] | None = None


def _get_roles_data() -> dict[str, dict]:
    """Load roadmap_skills.json once."""
    global _roles_data
    if _roles_data is None:
        path = Path("data/roadmap_skills.json")
        with open(path, "r", encoding="utf-8") as f:
            _roles_data = json.load(f)
    return _roles_data


def _get_role(role_id: str) -> dict | None:
    """Get role data by ID."""
    return _get_roles_data().get(role_id)


# ── LLM-based recommendations ─────────────────────────────────────────────

_RECOMMEND_PROMPT = """你是一个职业推荐 AI。根据用户的技能和背景，从以下岗位中推荐最匹配的 5 个方向。

【强制规则】
如果用户求职意向（job_target）不为空，则与求职意向最匹配的岗位必须出现在推荐中，且作为 entry 通道的第一个推荐，affinity_pct 不低于 85。这是用户的主观意愿，优先级高于任何技能分析。

【经验级别硬约束（必须严格执行，违反视为严重错误）】
- experience_years == 0 的用户（应届/在校学生）：
  * 禁止推荐 career_level == 4 的架构师岗位（software-architect、data-architect、ml-architect、security-architect、qa-lead、cloud-architect、engineering-manager），这些岗位招的是 5+ 年经验的资深工程师
  * 禁止推荐 career_level == 5 的总监/CTO 岗位（cto）
  * 即便应届生技能栈似乎沾边，架构师岗位永远不会招应届生
- experience_years <= 1 的用户：career_level >= 4 岗位 affinity_pct 必须 ≤ 35

【岗位画像对齐（命中 not_this_role_if 则不推）】
每个岗位的"不适合"条目是主动排除信号。用户情况命中即表明该岗位不合适：
- "初中级工程师" / "个人贡献者阶段" → 应届生和 experience_years < 3 的用户命中
- "主要做业务CRUD" / "无C++多线程/网络项目" → 看用户项目是否命中
- "主要用Java/Python" → 看用户核心语言
如果命中岗位的 not_this_role_if 中任一条，affinity_pct 必须 ≤ 30，不得进入 entry/growth 通道。

【技能家族亲和性】
推荐岗位的核心技能栈必须和用户核心技能栈同一家族。零交集跨家族推荐不得进入 entry/growth：
- C/C++ 系统背景（Linux 网络/多线程/epoll/TCP/Reactor）用户：优先 cpp、systems-cpp、storage-database-kernel、search-engine-engineer、server-side-game-developer。不得推 data-analyst、data-engineer、bi-analyst（技能栈零交集）除非用户 job_target 里明确写了数据方向
- 数据分析背景（SQL/Python/统计）用户：不得推 cpp、systems-cpp、rust（技能栈零交集）
- 前端背景（JS/React/CSS）用户：不得推 ai-engineer、algorithm-engineer（硬核信号不够）

【熟练度折算（严格执行）】
每个技能后面括号里是熟练度，affinity_pct 计算时必须按折算系数考虑：
  - expert / proficient / advanced → 1.0 完整技能点
  - intermediate                    → 0.5 技能点
  - familiar                        → 0.3 技能点
  - beginner                        → 0.2 技能点
举例：一个用户写了"机器学习(familiar)"，他只是"了解过"机器学习，**不能**作为推荐机器学习岗位的强信号。

【高门槛方向 affinity_pct 上限（违反视为严重错误）】
以下方向门槛远高于普通工程岗，没有硬核信号时 affinity_pct 必须受上限约束：

■ AI 数据科学家 / 机器学习工程师 / 算法工程师 / AI 工程师：
  硬核信号定义：
    (a) 论文发表（SCI / EI / CCF-A/B）
    (b) 学科竞赛奖（Kaggle 铜牌以上 / ACM / 数学建模国奖）
    (c) 独立实现过模型（不仅调用 sklearn.cluster / fit_predict）
    (d) 深度学习框架（PyTorch/TensorFlow）完整项目经历
  - 零硬核信号：affinity_pct ≤ 50
  - 1 条硬核信号：affinity_pct ≤ 60
  - 2+ 条硬核信号：可以 70+
  ⚠ "在项目里用过聚类算法分类用户" 不算硬核信号，那是数据分析的日常。

■ 数据分析师 / BI 分析师 / 数据运营：
  - 有 Python+Excel+SQL 其一 intermediate 以上 + 一段数据分析实习 → affinity_pct ≥ 80
  - 全满足 + 真实业务产出（用户画像/销售分析/报表）→ affinity_pct ≥ 85

■ 产品经理：
  - 偏业务思维岗位，不看硬技能只看业务理解。默认 50-65 区间，有产品实习或产品经历可到 75+

【岗位列表】
{role_list}

【用户求职意向（最高优先级）】
{job_target}

【用户技能（含熟练度）】
{user_skills}

【用户背景】
专业：{major}，学历：{degree}，工作年限：{exp_years}

分三个通道推荐：
- entry（起步岗位）：与求职意向最匹配的岗位排第一，当前技能+熟练度真实可胜任的 1-2 个
- growth（成长目标）：需要一定提升但方向自然的 1-2 个
- explore（探索方向）：跨领域但有潜力的 1 个

返回严格 JSON 数组，不要任何其他文字：
[{{"role_id": "岗位ID", "label": "中文名", "channel": "entry|growth|explore", "reason": "一句话推荐理由（必须提到熟练度）", "affinity_pct": 匹配度0到100}}]"""


# Keywords to role_id mapping for programmatic job_target override
# ⚠ 一定要各归各，不能把"数据分析"映射到"ai-data-scientist"（两个方向门槛差巨大）
_JOB_TARGET_ROLE_MAP = [
    (["产品经理", "product manager", "pm", "产品实习"], "product-manager"),
    (["前端", "frontend", "front-end", "web开发"], "frontend"),
    (["后端", "backend", "服务端", "java开发"], "java"),
    (["全栈", "full stack", "full-stack"], "full-stack"),
    (["算法", "algorithm", "研究员", "研究岗"], "algorithm-engineer"),
    (["机器学习", "ml工程", "machine learning"], "machine-learning"),
    (["ai工程", "ai engineer", "大模型", "llm"], "ai-engineer"),
    # 修复：数据分析 ≠ AI 数据科学家，两个方向门槛差巨大
    (["数据分析", "data analyst", "数据分析师"], "data-analyst"),
    (["数据科学", "data scientist", "ai数据"], "ai-data-scientist"),
    (["数据工程", "data engineer", "数据工程师"], "data-engineer"),
    (["bi", "商业智能", "bi分析"], "bi-analyst"),
    (["搜索引擎", "search engine"], "search-engine-engineer"),
    (["运维", "devops", "sre"], "devops"),
    (["安全", "security", "网络安全"], "cyber-security"),
    (["游戏", "game"], "game-developer"),
    (["c++", "c plus"], "cpp"),
    (["go", "golang"], "golang"),
    (["python工程师", "python developer"], "python"),
]


def _find_role_id_for_job_target(job_target: str) -> str | None:
    """Map job_target text to a role_id using keyword matching."""
    if not job_target or job_target == "未指定":
        return None
    target_lower = job_target.lower()
    for keywords, role_id in _JOB_TARGET_ROLE_MAP:
        if any(kw in target_lower for kw in keywords):
            return role_id
    return None


def _generate_recommendations(profile_data: dict, top_k: int = 5) -> dict:
    """Call LLM to generate recommendations. Returns response dict or None on failure."""
    from backend.llm import llm_chat, parse_json_response, get_model
    from backend.routers._profiles_graph import _get_role_list_text

    # Preserve level: pass full skill objects to downstream formatting
    skill_objs = [s for s in profile_data.get("skills", []) if isinstance(s, dict) and s.get("name")]
    if not skill_objs:
        return {"recommendations": [], "user_skill_count": 0}

    # Format skills with mastery level so LLM can calibrate affinity_pct
    # e.g. "Python(intermediate), 机器学习(familiar), SQL(familiar)"
    skills_with_level = ", ".join(
        f"{s.get('name')}({s.get('level') or 'unspecified'})" for s in skill_objs
    )

    job_target = profile_data.get("job_target", "") or "未指定"
    edu = profile_data.get("education", {})
    prompt = _RECOMMEND_PROMPT.format(
        role_list=_get_role_list_text(),
        job_target=job_target,
        user_skills=skills_with_level,
        major=edu.get("major", "未知"),
        degree=edu.get("degree", "未知"),
        exp_years=profile_data.get("experience_years", 0),
    )

    result = llm_chat([{"role": "user", "content": prompt}], model=get_model("fast"), temperature=0.1, timeout=60)
    recs = parse_json_response(result)
    if not isinstance(recs, list):
        return {"recommendations": [], "user_skill_count": len(skill_objs)}

    # Enrich with graph data
    graph_path = Path("data/graph.json")
    graph_nodes = {}
    if graph_path.exists():
        with open(graph_path, "r", encoding="utf-8") as f:
            for n in json.load(f).get("nodes", []):
                graph_nodes[n["node_id"]] = n

    enriched = []
    for r in recs[:top_k]:
        rid = r.get("role_id", "")
        node = graph_nodes.get(rid, {})
        enriched.append({
            "role_id": rid,
            "label": r.get("label", node.get("label", rid)),
            "affinity_pct": r.get("affinity_pct", 50),
            "matched_skills": [],
            "gap_skills": node.get("must_skills", [])[:4],
            "gap_hours": 0,
            "zone": node.get("zone", "safe"),
            "salary_p50": node.get("salary_p50", 0),
            "reason": r.get("reason", ""),
            "channel": r.get("channel", "entry"),
            "career_level": node.get("career_level", 0),
            "replacement_pressure": node.get("replacement_pressure", 50),
            "human_ai_leverage": node.get("human_ai_leverage", 50),
        })

    # ── Programmatic job_target override (double insurance) ──────────────────
    # If user explicitly stated a job target, ensure that role appears first.
    # Never rely solely on LLM to respect a hard constraint.
    target_role_id = _find_role_id_for_job_target(job_target)
    if target_role_id and target_role_id in graph_nodes:
        existing_ids = [r["role_id"] for r in enriched]
        if target_role_id in existing_ids:
            # Move it to front and set high affinity
            idx = existing_ids.index(target_role_id)
            target_rec = enriched.pop(idx)
            target_rec["affinity_pct"] = max(target_rec["affinity_pct"], 88)
            target_rec["channel"] = "entry"
            target_rec["reason"] = target_rec.get("reason") or f"与求职意向「{job_target}」高度吻合"
            enriched.insert(0, target_rec)
        else:
            # Not in LLM results at all — insert it
            node = graph_nodes[target_role_id]
            enriched.insert(0, {
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
                "replacement_pressure": node.get("replacement_pressure", 50),
                "human_ai_leverage": node.get("human_ai_leverage", 50),
            })
        logger.info("job_target override: moved %s to rank #1 (job_target=%s)", target_role_id, job_target)

    # ── Hard filter: seniority guardrails ──────────────────────────────────
    # LLM prompt 已经强调经验级别硬约束，但不能完全信任；程序兜底再过一遍。
    # experience_years == 0（应届/在校）绝对禁止推荐 L4+ 的架构师/经理/总监岗位。
    exp_years = profile_data.get("experience_years", 0) or 0
    before_filter = len(enriched)
    if exp_years == 0:
        enriched = [r for r in enriched if (r.get("career_level") or 0) <= 3]
    elif exp_years <= 1:
        enriched = [r for r in enriched if (r.get("career_level") or 0) <= 4]
    dropped = before_filter - len(enriched)
    if dropped:
        logger.info("Seniority filter: dropped %d senior recs for user (exp=%d)", dropped, exp_years)

    # 补齐至 top_k：如果过滤后不足，从 graph 里按技能重合度 + 职级合适回填
    if len(enriched) < top_k:
        user_skill_set = {
            (s.get("name") or "").lower().strip()
            for s in profile_data.get("skills", [])
            if isinstance(s, dict) and s.get("name")
        }
        existing_ids = {r["role_id"] for r in enriched}

        candidates = []
        for nid, node in graph_nodes.items():
            if nid in existing_ids:
                continue
            cl = node.get("career_level", 0) or 0
            if exp_years == 0 and cl > 3:
                continue
            if exp_years <= 1 and cl > 4:
                continue
            node_skills = {
                (s if isinstance(s, str) else s.get("name", "")).lower().strip()
                for s in (node.get("must_skills") or [])
            }
            overlap = len(user_skill_set & node_skills)
            if overlap == 0:
                continue
            candidates.append((overlap, nid, node))
        candidates.sort(key=lambda x: -x[0])

        backfilled = 0
        for overlap, nid, node in candidates:
            if len(enriched) >= top_k:
                break
            enriched.append({
                "role_id": nid,
                "label": node.get("label", nid),
                "affinity_pct": min(60 + overlap * 5, 78),
                "matched_skills": [],
                "gap_skills": (node.get("must_skills") or [])[:4],
                "gap_hours": 0,
                "zone": node.get("zone", "safe"),
                "salary_p50": node.get("salary_p50", 0),
                "reason": f"技能画像与该方向有 {overlap} 项重合",
                "channel": "growth",
                "career_level": node.get("career_level", 0),
                "replacement_pressure": node.get("replacement_pressure", 50),
                "human_ai_leverage": node.get("human_ai_leverage", 50),
            })
            backfilled += 1
        if backfilled:
            logger.info("Seniority backfill: added %d candidates by skill overlap", backfilled)

    return {"recommendations": enriched[:top_k], "user_skill_count": len(skill_objs)}


def _save_rec_cache(profile: Profile, p_hash: str, resp: dict, db: Session):
    """Persist recommendations to DB."""
    profile.cached_recs_json = json.dumps(
        {"hash": p_hash, "data": resp}, ensure_ascii=False
    )
    db.commit()


def _load_rec_cache(profile: Profile, p_hash: str) -> dict | None:
    """Load cached recommendations from DB. Returns None if stale or empty."""
    try:
        cached = json.loads(profile.cached_recs_json or "{}")
    except (json.JSONDecodeError, TypeError):
        return None
    if cached.get("hash") == p_hash and cached.get("data"):
        return cached["data"]
    return None


@router.get("")
def get_recommendations_endpoint(
    top_k: int = Query(5, ge=1, le=10),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get recommendations — returns DB-cached result if profile unchanged."""
    from backend.services.gap_analyzer import profile_hash

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        return {"recommendations": [], "user_skill_count": 0}

    profile_data = json.loads(profile.profile_json or "{}")
    p_hash = profile_hash(profile_data)

    # Try DB cache
    cached = _load_rec_cache(profile, p_hash)
    if cached:
        logger.debug("Recommendations DB cache hit for user %s", user.id)
        return cached

    # No cache — generate via LLM
    try:
        resp = _generate_recommendations(profile_data, top_k)
        if resp["recommendations"]:
            _save_rec_cache(profile, p_hash, resp, db)
        return resp
    except Exception as e:
        logger.warning("LLM recommendations failed: %s", e)
        return {"recommendations": [], "user_skill_count": len(
            [s for s in profile_data.get("skills", []) if isinstance(s, dict) and s.get("name")]
        )}


@router.post("/refresh")
def refresh_recommendations(
    top_k: int = Query(5, ge=1, le=10),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Force regenerate recommendations from LLM and persist to DB."""
    from backend.services.gap_analyzer import profile_hash

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(404, "请先建立画像")

    profile_data = json.loads(profile.profile_json or "{}")
    skills = [s.get("name", "") for s in profile_data.get("skills", []) if s.get("name")]
    if not skills:
        raise HTTPException(400, "画像中无技能数据，无法生成推荐")

    resp = _generate_recommendations(profile_data, top_k)
    p_hash = profile_hash(profile_data)
    _save_rec_cache(profile, p_hash, resp, db)
    return resp


# ── Gap analysis (LLM-based) ──────────────────────────────────────────────

@router.get("/gap-analysis")
def get_gap_analysis(
    role_id: str = Query(..., description="Target role node_id"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """LLM-based gap analysis: which roadmap modules has the user mastered vs needs to learn."""
    from backend.services.gap_analyzer import analyze_gaps, profile_hash

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(404, "请先建立画像")

    profile_data = json.loads(profile.profile_json or "{}")
    if not profile_data.get("skills"):
        raise HTTPException(400, "画像中无技能数据")

    # Check cache
    p_hash = profile_hash(profile_data)
    cache_key = (p_hash, role_id)
    if cache_key in _gap_cache:
        return _gap_cache[cache_key]

    # Get role info
    role = _get_role(role_id)
    if not role:
        raise HTTPException(404, "角色不存在")

    topics = role.get("topics", [])
    if not topics:
        topics = role.get("must_skills", [])
    role_label = role.get("label", role_id)

    result = analyze_gaps(profile_data, role_id, role_label, topics)

    # Merge user-confirmed mastered modules
    mastered_modules = profile_data.get("mastered_modules", {})
    confirmed_for_role = set(mastered_modules.get(role_id, []))
    if confirmed_for_role:
        new_gaps = []
        for g in result["gaps"]:
            if g["module"] in confirmed_for_role:
                result["mastered"].append({"module": g["module"], "reason": "用户自行确认已掌握"})
            else:
                new_gaps.append(g)
        result["gaps"] = new_gaps
        result["mastered_count"] = len(result["mastered"])
        result["gap_count"] = len(result["gaps"])
        total = result["mastered_count"] + result["gap_count"]
        result["coverage_pct"] = round(result["mastered_count"] / max(total, 1) * 100)

    if not result.get("failed"):
        _gap_cache[cache_key] = result
    return result


# ── Gap analysis detail (for MatchDetailPage) ─────────────────────────────

@router.get("/match-analysis/{role_id}")
def get_match_analysis_detail(
    role_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full LLM gap analysis detail for a specific role (DB-cached)."""
    from backend.services.gap_analyzer import analyze_gaps, profile_hash

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(404, "请先建立画像")

    profile_data = json.loads(profile.profile_json or "{}")
    p_hash = profile_hash(profile_data)

    role = _get_role(role_id)
    if not role:
        raise HTTPException(404, "角色不存在")

    role_label = role.get("label", role_id)

    # DB cache check
    cached = _load_gap_cache(profile, p_hash, role_id)
    if cached:
        cached["label"] = role_label
        return cached

    topics = role.get("topics", [])
    if not topics:
        topics = role.get("must_skills", [])

    result = analyze_gaps(profile_data, role_id, role_label, topics)
    result["label"] = role_label
    if not result.get("failed"):
        _save_gap_cache(profile, p_hash, role_id, result, db)
    return result


# ── Confirm mastered module ────────────────────────────────────────────────

class ConfirmMasteredRequest(BaseModel):
    role_id: str
    module: str


@router.post("/gap-analysis/confirm")
def confirm_mastered(
    req: ConfirmMasteredRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """User confirms they've mastered a module — removes it from gaps."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(404, "请先建立画像")

    profile_data = json.loads(profile.profile_json or "{}")
    mastered_modules = profile_data.get("mastered_modules", {})
    role_list = mastered_modules.get(req.role_id, [])
    if req.module not in role_list:
        role_list.append(req.module)
    mastered_modules[req.role_id] = role_list
    profile_data["mastered_modules"] = mastered_modules
    profile.profile_json = json.dumps(profile_data, ensure_ascii=False)
    db.commit()

    # Invalidate cache for this role
    from backend.services.gap_analyzer import profile_hash
    p_hash = profile_hash(profile_data)
    _gap_cache.pop((p_hash, req.role_id), None)

    return {"ok": True, "module": req.module, "role_id": req.role_id}
