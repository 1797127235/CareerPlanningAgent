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
from backend.db_models import JobNode, JobNodeIntro, LearningProgress, Profile, User
from backend.llm import get_llm_client, get_model
from backend.services.graph_service import get_graph_service
from backend.services.learning_service import get_learning_service

_ROLE_INTROS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "role_intros.json"
_role_intros: dict[str, dict] | None = None


def _get_role_intros() -> dict[str, dict]:
    global _role_intros
    if _role_intros is None:
        try:
            _role_intros = json.loads(_ROLE_INTROS_PATH.read_text(encoding="utf-8"))
        except Exception:
            _role_intros = {}
    return _role_intros

logger = logging.getLogger(__name__)

router = APIRouter()


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

    # Learning path topic count + user's completion progress
    learning_topic_count = 0
    learning_total_subtopics = 0
    learning_completed = 0
    learning_pct = 0
    try:
        svc = get_learning_service()
        lp = svc.get_learning_path(node_id)
        if lp:
            topics = lp.get("topics", [])
            learning_topic_count = len(topics)
            for t in topics:
                learning_total_subtopics += len(t.get("subtopics", []))
    except Exception:
        pass

    # User's completed subtopics for this role
    profile_for_progress = db.query(Profile).filter_by(user_id=user.id).first()
    if profile_for_progress and learning_total_subtopics > 0:
        completed_rows = (
            db.query(LearningProgress)
            .filter_by(profile_id=profile_for_progress.id, role_id=node_id, completed=True)
            .count()
        )
        learning_completed = completed_rows
        learning_pct = round(completed_rows / learning_total_subtopics * 100)

    # Dynamic promotion level based on learning progress
    def _pct_to_level(pct: int) -> int:
        if pct >= 90: return 5
        if pct >= 70: return 4
        if pct >= 45: return 3
        if pct >= 20: return 2
        return 1
    user_dynamic_level = _pct_to_level(learning_pct)

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

    return {
        **node,
        "terrain": terrain,
        "intro": intro_data.get("description") or intro_data.get("brief") or None,
        "promotion_targets": promotion_targets,
        "transition_targets": transition_targets,
        "learning_topic_count": learning_topic_count,
        "learning_progress": {
            "total_subtopics": learning_total_subtopics,
            "completed": learning_completed,
            "pct": learning_pct,
        },
        "user_dynamic_level": user_dynamic_level,
        "user_matched_skills": user_matched,
        "user_gap_skills": user_gaps,
        "match": match_result,
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


# ── Learning resources ─────────────────────────────────────────────────────

@router.get("/node/{node_id}/learning")
def get_node_learning(
    node_id: str,
    resource_type: str | None = Query(None, description="Filter: article/video/book/course/official"),
    limit: int = Query(0, ge=0, le=300, description="Max topics (0=all)"),
    offset: int = Query(0, ge=0, description="Skip N topics"),
    user: User = Depends(get_current_user),
):
    """Return learning topics + resources for a role node."""
    svc = get_learning_service()
    data = svc.get_role_topics(node_id, resource_type=resource_type, limit=limit, offset=offset)
    if data is None:
        raise HTTPException(404, "该角色暂无学习资源")
    return data


@router.get("/node/{node_id}/learning/summary")
def get_node_learning_summary(
    node_id: str,
    user: User = Depends(get_current_user),
):
    """Return topic/resource counts for a role (lightweight)."""
    svc = get_learning_service()
    summary = svc.get_role_summary(node_id)
    if summary is None:
        return {"role_id": node_id, "topic_count": 0, "resource_count": 0, "type_breakdown": {}}
    return summary


# ── Learning path (structured) ────────────────────────────────────────────


@router.get("/learning-path/{role_id}")
def get_learning_path(
    role_id: str,
    gap_topics: str | None = Query(None, description="Comma-separated topic titles to filter"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Structured learning path for a role, filtered to gap topics, with completion status."""
    profile = db.query(Profile).filter_by(user_id=user.id).first()
    if not profile:
        raise HTTPException(404, "未找到画像")

    # Get completed subtopic IDs from DB
    rows = (
        db.query(LearningProgress.subtopic_id)
        .filter_by(profile_id=profile.id, role_id=role_id, completed=True)
        .all()
    )
    completed_ids = {r[0] for r in rows}

    # Parse gap topics filter
    topics_filter = None
    if gap_topics:
        topics_filter = [t.strip() for t in gap_topics.split(",") if t.strip()]

    svc = get_learning_service()
    result = svc.get_learning_path(role_id, gap_topics=topics_filter, completed_ids=completed_ids)
    if result is None:
        raise HTTPException(404, "该角色暂无学习路径数据")
    return result


class ProgressUpdate(BaseModel):
    role_id: str
    subtopic_id: str
    completed: bool


@router.post("/learning-path/progress")
def update_learning_progress(
    body: ProgressUpdate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a subtopic as completed or uncompleted.

    When marking complete, fires a background task to:
    - Match topic → skill via semantic embedder
    - Update profile skills if matched
    - Create GrowthEvent with real readiness delta
    """
    profile = db.query(Profile).filter_by(user_id=user.id).first()
    if not profile:
        raise HTTPException(404, "未找到画像")

    existing = (
        db.query(LearningProgress)
        .filter_by(profile_id=profile.id, role_id=body.role_id, subtopic_id=body.subtopic_id)
        .first()
    )

    now = datetime.now(timezone.utc)
    is_newly_completed = False

    if existing:
        # Only fire background task when transitioning to completed
        is_newly_completed = body.completed and not existing.completed
        existing.completed = body.completed
        existing.completed_at = now if body.completed else None
    else:
        is_newly_completed = body.completed
        db.add(LearningProgress(
            profile_id=profile.id,
            role_id=body.role_id,
            subtopic_id=body.subtopic_id,
            completed=body.completed,
            completed_at=now if body.completed else None,
        ))

    db.commit()

    # Fire background task — does NOT block the response
    if is_newly_completed and profile:
        # Get topic title for skill matching (subtopic_id often IS the title or a readable key)
        # We use it directly as the topic_title for semantic matching
        topic_title = body.subtopic_id.replace("-", " ").replace("_", " ")

        from backend.services.growth_log_service import on_learning_completed
        background_tasks.add_task(
            on_learning_completed,
            user_id=user.id,
            profile_id=profile.id,
            subtopic_id=body.subtopic_id,
            topic_title=topic_title,
            role_id=body.role_id,
        )

    # Return updated progress summary
    total = (
        db.query(LearningProgress)
        .filter_by(profile_id=profile.id, role_id=body.role_id)
        .count()
    )
    done = (
        db.query(LearningProgress)
        .filter_by(profile_id=profile.id, role_id=body.role_id, completed=True)
        .count()
    )
    return {"ok": True, "completed": done, "total": total}


class SkillMasteryConfirm(BaseModel):
    skill_name: str
    level: str = "familiar"  # familiar | proficient


@router.post("/learning-path/confirm-skill")
def confirm_skill_mastery(
    body: SkillMasteryConfirm,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Student confirms they've mastered a skill → add/upgrade in profile."""
    profile = db.query(Profile).filter_by(user_id=user.id).first()
    if not profile:
        raise HTTPException(404, "未找到画像")

    profile_data = json.loads(profile.profile_json or "{}")
    skills = profile_data.get("skills", [])

    # Check if skill already exists
    existing_idx = next(
        (i for i, s in enumerate(skills) if s.get("name", "").lower() == body.skill_name.lower()),
        None,
    )

    level_order = ["beginner", "familiar", "proficient", "expert"]
    new_level = body.level if body.level in level_order else "familiar"

    if existing_idx is not None:
        # Upgrade only if new level is higher
        old_level = skills[existing_idx].get("level", "beginner")
        old_rank = level_order.index(old_level) if old_level in level_order else 0
        new_rank = level_order.index(new_level)
        if new_rank > old_rank:
            skills[existing_idx]["level"] = new_level
    else:
        skills.append({"name": body.skill_name, "level": new_level})

    profile_data["skills"] = skills
    profile.profile_json = json.dumps(profile_data, ensure_ascii=False)

    # Recompute quality (invalidates profile_hash → recommendations refresh)
    from backend.services.profile_service import ProfileService
    from backend.services.graph_service import get_graph_service
    ps = ProfileService(get_graph_service(db))
    quality = ps.compute_quality(profile_data)
    profile.quality_json = json.dumps(quality, ensure_ascii=False)

    # Clear cached recommendations (profile changed)
    profile.cached_recs_json = None

    # Compute match percentage against current goal
    from backend.db_models import CareerGoal
    match_pct = 0
    gap_remaining = 0
    goal = db.query(CareerGoal).filter_by(
        profile_id=profile.id, is_primary=True
    ).first()
    if goal and goal.gap_skills:
        user_skill_names = {s.get("name", "").lower() for s in skills}
        still_missing = [s for s in goal.gap_skills if s.lower() not in user_skill_names]
        gap_remaining = len(still_missing)
        # match_pct = matched skills / total must_skills for this role
        g = get_graph_service(db)
        node = g.get_node(goal.target_node_id) if g else None
        must_skills = (node.get("must_skills") or []) if node else goal.gap_skills
        total_must = len(must_skills) if must_skills else len(goal.gap_skills)
        if total_must > 0:
            matched_must = sum(1 for s in must_skills if s.lower() in user_skill_names)
            match_pct = round(matched_must / total_must * 100)

    db.commit()
    return {
        "ok": True,
        "skill": body.skill_name,
        "level": new_level,
        "match_pct": match_pct,
        "gap_remaining": gap_remaining,
    }
