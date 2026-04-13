"""Graph router — terrain map, node detail, escape routes."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import get_db
from backend.db_models import JobNode, JobNodeIntro, Profile, User
from backend.llm import get_llm_client, get_model
from backend.services.graph_service import get_graph_service

_ROLE_INTROS_PATH   = Path(__file__).resolve().parent.parent.parent / "data" / "role_intros.json"
_SIGNALS_PATH       = Path(__file__).resolve().parent.parent.parent / "data" / "market_signals.json"
_INDUSTRY_PATH      = Path(__file__).resolve().parent.parent.parent / "data" / "industry_signals.json"
_role_intros:   dict[str, dict] | None = None
_market_signals: dict[str, dict] | None = None
_industry_signals: dict[str, list] | None = None


def _get_role_intros() -> dict[str, dict]:
    global _role_intros
    if _role_intros is None:
        try:
            _role_intros = json.loads(_ROLE_INTROS_PATH.read_text(encoding="utf-8"))
        except Exception:
            _role_intros = {}
    return _role_intros


def _get_market_signals() -> dict[str, dict]:
    global _market_signals
    if _market_signals is None:
        try:
            _market_signals = json.loads(_SIGNALS_PATH.read_text(encoding="utf-8"))
        except Exception:
            _market_signals = {}
    return _market_signals


def _get_industry_signals() -> dict[str, list]:
    global _industry_signals
    if _industry_signals is None:
        try:
            _industry_signals = json.loads(_INDUSTRY_PATH.read_text(encoding="utf-8"))
        except Exception:
            _industry_signals = {}
    return _industry_signals


logger = logging.getLogger(__name__)

router = APIRouter()


# ── Market signals endpoint ───────────────────────────────────────────────────

@router.get("/market-signals")
def get_market_signals(user: User = Depends(get_current_user)):
    """Return precomputed market decision signals for all role_families.

    Used by GraphPage to color-code nodes and by RoleDetailPage for timing panel.
    Data is precomputed by etl/03_signals.py — zero DB query, JSON file read.
    """
    signals = _get_market_signals()
    industry = _get_industry_signals()
    # Attach top-3 industry breakdown to each family signal
    result = {}
    for fam, sig in signals.items():
        entry = dict(sig)
        entry["top_industries"] = industry.get(fam, [])[:3]
        result[fam] = entry
    return result


# ── Full map ─────────────────────────────────────────────────────────────────

@router.get("/map")
def get_map(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all graph nodes + edges for 3D visualization."""
    g = get_graph_service(db)
    # Pre-compute edge degrees (undirected)
    edge_list = g._get_edges_with_type()
    degree: dict[str, int] = {nid: 0 for nid in g.node_ids}
    for s, t, _et in edge_list:
        degree[s] = degree.get(s, 0) + 1
        degree[t] = degree.get(t, 0) + 1

    nodes = []
    for nid in g.node_ids:
        node = g.get_node(nid)
        if node:
            raw_skills = node.get("must_skills") or []
            must_skills = raw_skills[:4] if isinstance(raw_skills, list) else []
            nodes.append({
                "node_id": node.get("node_id"),
                "label": node.get("label"),
                "role_family": node.get("role_family"),
                "zone": node.get("zone", "transition"),
                "replacement_pressure": node.get("replacement_pressure", 50),
                "human_ai_leverage": node.get("human_ai_leverage", 50),
                "salary_p50": node.get("salary_p50"),
                "career_level": node.get("career_level", 2),
                "must_skills": must_skills,
                "skill_count": node.get("skill_count", 0),
                "degree": degree.get(nid, 0),
                "soft_skills": node.get("soft_skills", {}),
                "promotion_path": node.get("promotion_path", []),
            })
    edges = [{"source": s, "target": t, "edge_type": et} for s, t, et in edge_list]
    info = g.info()
    return {"nodes": nodes, "edges": edges, "node_count": info["node_count"], "edge_count": info["edge_count"]}


# ── Node detail ──────────────────────────────────────────────────────────────

@router.get("/node/{node_id}")
def get_node(
    node_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Single node detail + terrain scores + role intro + career trajectory."""
    g = get_graph_service(db)
    node = g.get_node(node_id)
    if not node:
        raise HTTPException(404, "节点不存在")
    terrain = g.get_terrain_score(node_id, db)
    intro_data = _get_role_intros().get(node_id, {})

    # Career trajectory: promotion targets (vertical edges) + transition targets (horizontal)
    graph_path = Path(__file__).resolve().parent.parent.parent / "data" / "graph.json"
    try:
        graph_data = json.loads(graph_path.read_text(encoding="utf-8"))
        edges = graph_data.get("edges", [])
        nodes_map = {n["node_id"]: n for n in graph_data.get("nodes", [])}
    except Exception:
        edges, nodes_map = [], {}

    promotion_targets = []
    transition_targets = []
    for e in edges:
        if e["source"] == node_id:
            target_node = nodes_map.get(e["target"], {})
            if not target_node:
                continue
            entry = {
                "node_id": e["target"],
                "label": target_node.get("label", e["target"]),
                "zone": target_node.get("zone", ""),
                "career_level": target_node.get("career_level", 0),
            }
            if e.get("edge_type") == "vertical":
                promotion_targets.append(entry)
            else:
                transition_targets.append(entry)

    # 学习路径已砍 — user_dynamic_level 默认 1，前端不再依赖学习进度晋升
    user_dynamic_level = 1

    # User's skill match + multi-dimensional matching (if profile exists)
    user_matched = []
    user_gaps = []
    match_result = None
    profile = db.query(Profile).filter_by(user_id=user.id).first()
    if profile:
        profile_data = json.loads(profile.profile_json or "{}")
        user_skills_lower = {
            s.get("name", "").lower()
            for s in profile_data.get("skills", [])
            if isinstance(s, dict) and s.get("name")
        }
        for skill in node.get("must_skills", []):
            if skill.lower() in user_skills_lower:
                user_matched.append(skill)
            else:
                user_gaps.append(skill)

        # Multi-dimensional matching
        from backend.services.matching_service import compute_match
        match_result = compute_match(profile_data, node)

    # Attach market signal for this node's role_family
    role_family = node.get("role_family", "")
    signals_map = _get_market_signals()
    industry_map = _get_industry_signals()
    market_signal = signals_map.get(role_family)
    if market_signal:
        market_signal = {
            **market_signal,
            "top_industries": industry_map.get(role_family, [])[:3],
        }

    return {
        **node,
        "terrain": terrain,
        "intro": intro_data.get("description") or intro_data.get("brief") or None,
        "promotion_targets": promotion_targets,
        "transition_targets": transition_targets,
        "user_dynamic_level": user_dynamic_level,
        "user_matched_skills": user_matched,
        "user_gap_skills": user_gaps,
        "match": match_result,
        "market_signal": market_signal,
    }


# ── Escape routes ────────────────────────────────────────────────────────────

@router.get("/escape-routes")
def get_escape_routes(
    node_id: str = Query(..., description="起点节点 ID"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compute escape routes from a node, personalized to user's actual skills."""
    import json
    from backend.db_models import Profile
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    profile_skills: list[str] = []
    if profile:
        data = json.loads(profile.profile_json or "{}")
        profile_skills = [s.get("name", "") for s in data.get("skills", []) if s.get("name")]
    g = get_graph_service(db)
    raw_routes = g.find_escape_routes(node_id, profile_skills=profile_skills, db_session=db)
    # Transform to match frontend EscapeRoute type
    routes = []
    for r in raw_routes:
        gap = r.get("gap_skills", [])
        routes.append({
            "target_node_id": r.get("target", ""),
            "target_label": r.get("target_label", ""),
            "gap_skills": [g["name"] if isinstance(g, dict) else str(g) for g in gap],
            "estimated_hours": r.get("total_hours", 0),
            "safety_gain": r.get("safety_gain", 0),
            "tag": r.get("tag", ""),
            "target_zone": r.get("target_zone", "transition"),
            "salary_p50": r.get("salary_p50", 0),
        })
    return {"node_id": node_id, "routes": routes}


# ── Set career goal ─────────────────────────────────────────────────────────

class SetCareerGoalRequest(BaseModel):
    target_node_id: str
    target_label: str
    target_zone: str
    gap_skills: list[str] = []
    estimated_hours: int = 0
    safety_gain: float = 0.0
    salary_p50: int = 0


@router.put("/career-goal")
def set_career_goal(
    req: SetCareerGoalRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set (or update) the career goal for the current user's profile."""
    from backend.db_models import CareerGoal, Profile

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(404, "请先上传简历建立画像")
    profile_id = profile.id

    goal = (
        db.query(CareerGoal)
        .filter_by(profile_id=profile_id, user_id=user.id, is_active=True)
        .first()
    )

    # If empty target_node_id, deactivate the current goal (user wants to re-choose)
    if not req.target_node_id:
        if goal:
            goal.is_active = False
            goal.is_primary = False
            db.commit()
        return {"ok": True, "cleared": True}

    if goal is None:
        # No active goal — create a new one (e.g., after clearing previous goal)
        # Find from_node_id from last inactive goal
        prev = (
            db.query(CareerGoal)
            .filter_by(profile_id=profile_id, user_id=user.id)
            .order_by(CareerGoal.set_at.desc())
            .first()
        )
        goal = CareerGoal(
            user_id=user.id,
            profile_id=profile_id,
            from_node_id=prev.from_node_id if prev else "",
            target_node_id=req.target_node_id,
            target_label=req.target_label,
            target_zone=req.target_zone,
            gap_skills=req.gap_skills,
            total_hours=req.estimated_hours,
            safety_gain=req.safety_gain,
            salary_p50=req.salary_p50,
            is_primary=True,
            is_active=True,
        )
        db.add(goal)
        db.commit()
        return {"ok": True, "target_label": req.target_label, "target_zone": req.target_zone}

    goal.target_node_id = req.target_node_id
    goal.target_label = req.target_label
    goal.target_zone = req.target_zone
    goal.gap_skills = req.gap_skills
    goal.total_hours = req.estimated_hours
    goal.safety_gain = req.safety_gain
    goal.salary_p50 = req.salary_p50
    goal.set_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "target_label": req.target_label, "target_zone": req.target_zone}


# ── Patch career-goal gaps only ──────────────────────────────────────────────

class PatchGapsRequest(BaseModel):
    gap_skills: list[str]
    source: str = "jd_diagnosis"  # for audit trail


@router.patch("/career-goal/gaps")
def patch_career_goal_gaps(
    req: PatchGapsRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update gap_skills on the primary career goal without touching target/zone.

    Called after JD diagnosis: student elects to 'apply gap skills to learning path'.
    Creates a goal record if one does not yet exist (no target set).
    """
    from backend.db_models import CareerGoal, Profile

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(404, "请先上传简历建立画像")

    goal = (
        db.query(CareerGoal)
        .filter_by(profile_id=profile.id, user_id=user.id, is_active=True, is_primary=True)
        .first()
    )

    clean_gaps = [s.strip() for s in req.gap_skills if s.strip()][:20]

    if goal:
        goal.gap_skills = clean_gaps
        goal.set_at = datetime.now(timezone.utc)
    else:
        # No goal yet — create a placeholder goal with just gap_skills
        # target_node_id will be filled when student picks a role on graph page
        goal = CareerGoal(
            user_id=user.id,
            profile_id=profile.id,
            from_node_id="",
            target_node_id="",
            target_label="待设定目标岗位",
            target_zone="transition",
            gap_skills=clean_gaps,
            is_primary=True,
            is_active=True,
        )
        db.add(goal)

    db.commit()
    return {"ok": True, "gap_count": len(clean_gaps), "target_label": goal.target_label}


# ── Multi-goal CRUD ──────────────────────────────────────────────────────────

@router.get("/career-goals")
def list_career_goals(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all active career goals for the current user's profile."""
    from backend.db_models import CareerGoal, Profile, JobNode

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        return {"goals": []}

    goals = (
        db.query(CareerGoal)
        .filter_by(profile_id=profile.id, user_id=user.id, is_active=True)
        .order_by(CareerGoal.is_primary.desc(), CareerGoal.set_at.desc())
        .all()
    )

    graph_svc = get_graph_service(db)
    result = []
    for g in goals:
        # Resolve from_node label: try graph first, then DB, then raw ID
        graph_from = graph_svc.get_node(g.from_node_id)
        from_label = (
            graph_from.get("label") if graph_from
            else (lambda n: n.label if n else g.from_node_id)(
                db.query(JobNode).filter(JobNode.node_id == g.from_node_id).first()
            )
        )
        result.append({
            "id": g.id,
            "target_node_id": g.target_node_id,
            "target_label": g.target_label,
            "target_zone": g.target_zone,
            "from_node_id": g.from_node_id,
            "from_node_label": from_label,
            "gap_skills": g.gap_skills or [],
            "total_hours": g.total_hours or 0,
            "safety_gain": g.safety_gain or 0.0,
            "salary_p50": g.salary_p50 or 0,
            "is_primary": g.is_primary,
            "set_at": g.set_at.isoformat() if g.set_at else None,
        })

    return {"goals": result}


class AddCareerGoalRequest(BaseModel):
    target_node_id: str
    target_label: str
    target_zone: str
    gap_skills: list[str] = []
    estimated_hours: int = 0
    safety_gain: float = 0.0
    salary_p50: int = 0
    set_as_primary: bool = False


@router.post("/career-goals")
def add_career_goal(
    req: AddCareerGoalRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a new career goal direction. Does NOT overwrite existing goals."""
    from backend.db_models import CareerGoal, Profile
    from datetime import datetime, timezone

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(404, "请先建立画像")

    # 获取 from_node_id（从现有主目标或任意active goal）
    primary = (
        db.query(CareerGoal)
        .filter_by(profile_id=profile.id, user_id=user.id, is_active=True, is_primary=True)
        .first()
    )
    any_goal = primary or (
        db.query(CareerGoal)
        .filter_by(profile_id=profile.id, user_id=user.id, is_active=True)
        .first()
    )
    if not any_goal:
        raise HTTPException(400, "请先建立画像并完成图谱定位")

    # 检查该节点是否已经是目标
    existing = (
        db.query(CareerGoal)
        .filter_by(
            profile_id=profile.id,
            user_id=user.id,
            target_node_id=req.target_node_id,
            is_active=True,
        )
        .first()
    )
    if existing:
        raise HTTPException(400, "该岗位已经是目标方向")

    # 若设为主目标，先取消其他主目标
    if req.set_as_primary:
        db.query(CareerGoal).filter_by(
            profile_id=profile.id, user_id=user.id, is_active=True, is_primary=True
        ).update({"is_primary": False})

    new_goal = CareerGoal(
        user_id=user.id,
        profile_id=profile.id,
        from_node_id=any_goal.from_node_id,
        target_node_id=req.target_node_id,
        target_label=req.target_label,
        target_zone=req.target_zone,
        gap_skills=req.gap_skills,
        total_hours=req.estimated_hours,
        safety_gain=req.safety_gain,
        salary_p50=req.salary_p50,
        is_primary=req.set_as_primary,
        is_active=True,
        set_at=datetime.now(timezone.utc),
    )
    db.add(new_goal)
    db.commit()
    db.refresh(new_goal)

    return {"ok": True, "goal_id": new_goal.id, "target_label": req.target_label}


@router.delete("/career-goals/{goal_id}")
def remove_career_goal(
    goal_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deactivate a career goal direction."""
    from backend.db_models import CareerGoal
    from datetime import datetime, timezone

    goal = db.query(CareerGoal).filter_by(id=goal_id, user_id=user.id, is_active=True).first()
    if not goal:
        raise HTTPException(404, "目标不存在")

    # 不允许删除唯一的active goal（防止空状态）
    active_count = (
        db.query(CareerGoal)
        .filter_by(profile_id=goal.profile_id, user_id=user.id, is_active=True)
        .count()
    )
    if active_count <= 1:
        raise HTTPException(400, "至少保留一个目标方向")

    goal.is_active = False
    goal.cleared_at = datetime.now(timezone.utc)

    # 若删除的是主目标，自动将最新的goal设为主目标
    if goal.is_primary:
        next_goal = (
            db.query(CareerGoal)
            .filter(
                CareerGoal.profile_id == goal.profile_id,
                CareerGoal.user_id == user.id,
                CareerGoal.is_active == True,
                CareerGoal.id != goal_id,
            )
            .order_by(CareerGoal.set_at.desc())
            .first()
        )
        if next_goal:
            next_goal.is_primary = True

    db.commit()
    return {"ok": True}


@router.put("/career-goals/{goal_id}/primary")
def set_primary_career_goal(
    goal_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set a career goal as the primary direction."""
    from backend.db_models import CareerGoal

    goal = db.query(CareerGoal).filter_by(id=goal_id, user_id=user.id, is_active=True).first()
    if not goal:
        raise HTTPException(404, "目标不存在")

    # 取消其他主目标
    db.query(CareerGoal).filter(
        CareerGoal.profile_id == goal.profile_id,
        CareerGoal.user_id == user.id,
        CareerGoal.is_active == True,
        CareerGoal.id != goal_id,
    ).update({"is_primary": False})

    goal.is_primary = True
    db.commit()

    return {"ok": True, "primary_label": goal.target_label}


# ── Node intro (LLM-generated, cached) ───────────────────────────────────────

@router.get("/node/{node_id}/intro")
def get_node_intro(
    node_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return a short LLM-generated intro for the node. Generated once then cached."""
    # Serve from cache if available
    cached = db.query(JobNodeIntro).filter_by(node_id=node_id).first()
    if cached:
        return {"node_id": node_id, "intro": cached.intro}

    # Fetch node data — try graph first (roadmap-based), then DB (legacy)
    g = get_graph_service(db)
    graph_node = g.get_node(node_id)
    db_node = db.query(JobNode).filter_by(node_id=node_id).first()

    if not graph_node and not db_node:
        raise HTTPException(404, "节点不存在")

    # Prefer graph data (roadmap), fall back to DB (legacy)
    node_label = (graph_node or {}).get("label") or (db_node.label if db_node else node_id)
    skills_raw = (graph_node or {}).get("must_skills") or (
        db_node.must_skills if db_node and isinstance(db_node.must_skills, list) else []
    )
    tasks_raw = (graph_node or {}).get("core_tasks") or (
        db_node.core_tasks if db_node and isinstance(db_node.core_tasks, list) else []
    )
    industries_raw = (
        db_node.top_industries if db_node and isinstance(db_node.top_industries, list) else []
    )
    skills = ", ".join(str(s) for s in skills_raw[:5]) or "通用技能"
    tasks = "、".join(str(t) for t in tasks_raw[:3]) or "日常工作"
    industries = "、".join(str(i) for i in industries_raw[:2]) or "互联网"

    prompt = (
        f"请用2-3句话简洁介绍「{node_label}」岗位。"
        f"主要职责包括：{tasks}。"
        f"核心技能要求：{skills}。"
        f"常见行业：{industries}。"
        f"语言专业简洁，帮助求职者快速了解该岗位。直接输出介绍，不要标题或序号。"
    )

    try:
        client = get_llm_client(timeout=15)
        resp = client.chat.completions.create(
            model=get_model("fast"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.5,
        )
        intro = (resp.choices[0].message.content or "").strip()
        if not intro:
            raise ValueError("empty response")
    except Exception as e:
        logger.warning("node intro LLM failed for %s: %s", node_id, e)
        role_family = (graph_node or {}).get("role_family") or (db_node.role_family if db_node else "技术")
        intro = f"{node_label}是一个{role_family}方向的岗位，负责{tasks}，需要掌握{skills}等核心技能。"

    # Cache — guard against concurrent insert on same node_id (UNIQUE constraint)
    try:
        db.add(JobNodeIntro(node_id=node_id, intro=intro))
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(JobNodeIntro).filter_by(node_id=node_id).first()
        if existing:
            return {"node_id": node_id, "intro": existing.intro}

    return {"node_id": node_id, "intro": intro}


# ── Search ───────────────────────────────────────────────────────────────────

@router.get("/search")
def search_nodes(
    q: str = Query(..., description="搜索关键词"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search graph nodes by keyword."""
    g = get_graph_service(db)
    results = g.search_nodes(q)
    return {
        "query": q,
        "results": [
            {
                "node_id": n.get("node_id"),
                "label": n.get("label"),
                "role_family": n.get("role_family"),
                "zone": n.get("zone", "transition"),
            }
            for n in results[:20]
        ],
    }


