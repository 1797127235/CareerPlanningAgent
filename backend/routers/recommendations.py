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

【岗位列表】
{role_list}

【用户技能】
{user_skills}

【用户背景】
专业：{major}，学历：{degree}，工作年限：{exp_years}

分三个通道推荐：
- entry（起步岗位）：当前技能最匹配，可以直接胜任的 1-2 个
- growth（成长目标）：需要一定提升但方向自然的 1-2 个
- explore（探索方向）：跨领域但有潜力的 1 个

返回严格 JSON 数组，不要任何其他文字：
[{{"role_id": "岗位ID", "label": "中文名", "channel": "entry|growth|explore", "reason": "一句话推荐理由", "affinity_pct": 匹配度0到100}}]"""


def _generate_recommendations(profile_data: dict, top_k: int = 5) -> dict:
    """Call LLM to generate recommendations. Returns response dict or None on failure."""
    from backend.llm import llm_chat, parse_json_response, get_model
    from backend.routers.profiles import _get_role_list_text

    skills = [s.get("name", "") for s in profile_data.get("skills", []) if s.get("name")]
    if not skills:
        return {"recommendations": [], "user_skill_count": 0}

    edu = profile_data.get("education", {})
    prompt = _RECOMMEND_PROMPT.format(
        role_list=_get_role_list_text(),
        user_skills=", ".join(skills),
        major=edu.get("major", "未知"),
        degree=edu.get("degree", "未知"),
        exp_years=profile_data.get("experience_years", 0),
    )

    result = llm_chat([{"role": "user", "content": prompt}], model=get_model("fast"), temperature=0.1, timeout=60)
    recs = parse_json_response(result)
    if not isinstance(recs, list):
        return {"recommendations": [], "user_skill_count": len(skills)}

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
    return {"recommendations": enriched, "user_skill_count": len(skills)}


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
