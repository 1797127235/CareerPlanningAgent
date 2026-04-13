"""成长档案路由 — 项目记录 / 面试记录 / 学习记录。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import get_db
from backend.db_models import (
    InterviewRecord,
    LearningNote,
    Profile,
    ProjectLog,
    ProjectRecord,
    User,
)
from backend.services.growth_log_service import (
    generate_interview_analysis,
)

router = APIRouter()


def _get_profile_id(user: User, db: Session) -> int | None:
    profile = db.query(Profile).filter(Profile.user_id == user.id).order_by(Profile.id.desc()).first()
    return profile.id if profile else None


def _get_profile_skills(profile_id: int | None, db: Session) -> list[str]:
    if not profile_id:
        return []
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        return []
    try:
        data = json.loads(profile.profile_json)
        skills = data.get("skills", [])
        if skills and isinstance(skills[0], dict):
            return [s.get("name", "") for s in skills if s.get("name")]
        return [s for s in skills if isinstance(s, str)]
    except Exception:
        return []


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    name: str
    description: Optional[str] = None
    skills_used: list[str] = []
    gap_skill_links: list[str] = []     # 项目补哪些 gap 技能
    github_url: Optional[str] = None
    status: str = "in_progress"        # planning | in_progress | completed
    linked_node_id: Optional[str] = None
    reflection: Optional[str] = None
    started_at: Optional[str] = None


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    skills_used: Optional[list[str]] = None
    gap_skill_links: Optional[list[str]] = None
    github_url: Optional[str] = None
    status: Optional[str] = None
    linked_node_id: Optional[str] = None
    reflection: Optional[str] = None


class CreateInterviewRequest(BaseModel):
    company: str
    position: str = ""
    round: str = "技术一面"
    content_summary: str
    self_rating: str = "medium"        # good | medium | bad
    result: str = "pending"            # passed | failed | pending
    reflection: Optional[str] = None
    interview_at: Optional[str] = None
    application_id: Optional[int] = None


class UpdateInterviewRequest(BaseModel):
    result: Optional[str] = None
    reflection: Optional[str] = None
    self_rating: Optional[str] = None


# ── Timeline ──────────────────────────────────────────────────────────────────

@router.get("/dashboard")
def get_growth_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取成长看板数据：目标方向 + 分层技能覆盖率 + 匹配度曲线。"""
    from backend.db_models import CareerGoal, GrowthSnapshot
    from backend.services.graph_service import GraphService
    from backend.services.growth_log_service import _skill_matches

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        return {"has_goal": False, "has_profile": False}

    goal = (
        db.query(CareerGoal)
        .filter(
            CareerGoal.user_id == user.id,
            CareerGoal.profile_id == profile.id,
            CareerGoal.is_active == True,
        )
        .order_by(CareerGoal.is_primary.desc(), CareerGoal.set_at.desc())
        .first()
    )

    if not goal or not goal.target_node_id:
        return {"has_goal": False, "has_profile": True}

    svc = GraphService()
    svc.load()
    node = svc.get_node(goal.target_node_id)
    if not node:
        return {"has_goal": False, "has_profile": True}

    # Build user skill set
    try:
        profile_data = json.loads(profile.profile_json or "{}")
    except Exception:
        profile_data = {}
    raw_skills = profile_data.get("skills", [])
    if raw_skills and isinstance(raw_skills[0], dict):
        user_skills = {s.get("name", "").lower().strip() for s in raw_skills if s.get("name")}
    else:
        user_skills = {s.lower().strip() for s in raw_skills if isinstance(s, str) and s.strip()}

    # Tiered skill coverage
    tiers = node.get("skill_tiers", {}) or {}
    core_list = tiers.get("core", []) or []
    imp_list = tiers.get("important", []) or []
    bonus_list = tiers.get("bonus", []) or []

    def _count_matched(skills_list):
        matched_items = [s for s in skills_list if _skill_matches(s.get("name", ""), user_skills)]
        return len(matched_items), [s.get("name") for s in matched_items]

    core_cnt, core_matched = _count_matched(core_list)
    imp_cnt, imp_matched = _count_matched(imp_list)
    bonus_cnt, bonus_matched = _count_matched(bonus_list)

    def _pct(cnt: int, total: int) -> int:
        return int(round(cnt / total * 100)) if total > 0 else 0

    # Missing (gap) skills for each tier — for project form selector
    core_missing = [s.get("name") for s in core_list if not _skill_matches(s.get("name", ""), user_skills)]
    imp_missing = [s.get("name") for s in imp_list if not _skill_matches(s.get("name", ""), user_skills)]

    # Readiness curve from GrowthSnapshot (up to last 12 points)
    snapshots = (
        db.query(GrowthSnapshot)
        .filter(GrowthSnapshot.profile_id == profile.id)
        .order_by(GrowthSnapshot.created_at.asc())
        .limit(12)
        .all()
    )
    curve = [
        {
            "date": s.created_at.strftime("%m/%d") if s.created_at else "",
            "score": round(s.readiness_score or 0, 1),
        }
        for s in snapshots
    ]

    # Days since journey started (profile creation date)
    start_date = profile.created_at
    days_since_start = (datetime.now(timezone.utc) - start_date.replace(tzinfo=timezone.utc)).days if start_date else 0

    return {
        "has_goal": True,
        "has_profile": True,
        "goal": {
            "target_node_id": goal.target_node_id,
            "target_label": goal.target_label,
        },
        "days_since_start": days_since_start,
        "skill_coverage": {
            "core": {
                "covered": core_cnt,
                "total": len(core_list),
                "pct": _pct(core_cnt, len(core_list)),
                "matched": core_matched,
                "missing": core_missing,
            },
            "important": {
                "covered": imp_cnt,
                "total": len(imp_list),
                "pct": _pct(imp_cnt, len(imp_list)),
                "matched": imp_matched,
                "missing": imp_missing,
            },
            "bonus": {
                "covered": bonus_cnt,
                "total": len(bonus_list),
                "pct": _pct(bonus_cnt, len(bonus_list)),
            },
        },
        "gap_skills": goal.gap_skills or [],  # For project form selector
        "readiness_curve": curve,
    }


# ── Projects ──────────────────────────────────────────────────────────────────

@router.get("/projects")
def list_projects(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户所有项目记录。"""
    projects = (
        db.query(ProjectRecord)
        .filter(ProjectRecord.user_id == user.id)
        .order_by(ProjectRecord.created_at.desc())
        .all()
    )
    return {"projects": [_serialize_project(p) for p in projects]}


@router.post("/projects", status_code=201)
def create_project(
    req: CreateProjectRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建项目记录。"""
    profile_id = _get_profile_id(user, db)

    started_at = None
    if req.started_at:
        try:
            started_at = datetime.fromisoformat(req.started_at)
        except ValueError:
            pass

    completed_at = datetime.now(timezone.utc) if req.status == "completed" else None

    project = ProjectRecord(
        user_id=user.id,
        profile_id=profile_id,
        name=req.name,
        description=req.description,
        skills_used=req.skills_used,
        gap_skill_links=req.gap_skill_links,
        github_url=req.github_url,
        status=req.status,
        linked_node_id=req.linked_node_id,
        reflection=req.reflection,
        started_at=started_at or datetime.now(timezone.utc),
        completed_at=completed_at,
    )
    db.add(project)
    db.flush()
    db.commit()
    db.refresh(project)
    return _serialize_project(project)


@router.patch("/projects/{project_id}")
def update_project(
    project_id: int,
    req: UpdateProjectRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新项目记录。"""
    project = db.query(ProjectRecord).filter(
        ProjectRecord.id == project_id,
        ProjectRecord.user_id == user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    prev_status = project.status

    if req.name is not None:
        project.name = req.name
    if req.description is not None:
        project.description = req.description
    if req.skills_used is not None:
        project.skills_used = req.skills_used
    if req.gap_skill_links is not None:
        project.gap_skill_links = req.gap_skill_links
    if req.github_url is not None:
        project.github_url = req.github_url
    if req.linked_node_id is not None:
        project.linked_node_id = req.linked_node_id
    if req.reflection is not None:
        project.reflection = req.reflection
    if req.status is not None:
        project.status = req.status
        if req.status == "completed" and prev_status != "completed":
            project.completed_at = datetime.now(timezone.utc)

    db.flush()
    db.commit()
    db.refresh(project)
    return _serialize_project(project)


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(ProjectRecord).filter(
        ProjectRecord.id == project_id,
        ProjectRecord.user_id == user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    db.delete(project)
    db.commit()


def _serialize_project(p: ProjectRecord) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "skills_used": p.skills_used or [],
        "gap_skill_links": p.gap_skill_links or [],
        "github_url": p.github_url,
        "status": p.status,
        "linked_node_id": p.linked_node_id,
        "reflection": p.reflection,
        "started_at": p.started_at.isoformat() if p.started_at else None,
        "completed_at": p.completed_at.isoformat() if p.completed_at else None,
        "created_at": p.created_at.isoformat(),
        "graph_data": p.graph_data,
    }


# ── Project Graph ─────────────────────────────────────────────────────────────

class SaveGraphRequest(BaseModel):
    nodes: list[dict]
    edges: list[dict]


@router.get("/projects/{project_id}/graph")
def get_project_graph(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取项目节点图数据。"""
    project = db.query(ProjectRecord).filter(
        ProjectRecord.id == project_id,
        ProjectRecord.user_id == user.id,
    ).first()
    if not project:
        raise HTTPException(404, "项目不存在")
    data = project.graph_data or {"nodes": [], "edges": []}
    return data


@router.patch("/projects/{project_id}/graph")
def save_project_graph(
    project_id: int,
    req: SaveGraphRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """保存项目节点图数据。"""
    project = db.query(ProjectRecord).filter(
        ProjectRecord.id == project_id,
        ProjectRecord.user_id == user.id,
    ).first()
    if not project:
        raise HTTPException(404, "项目不存在")
    project.graph_data = {"nodes": req.nodes, "edges": req.edges}
    db.commit()
    return {"ok": True}


# ── Project Logs ─────────────────────────────────────────────────────────────

class CreateProjectLogRequest(BaseModel):
    content: str
    reflection: Optional[str] = None
    task_status: str = "done"   # done | in_progress | blocked
    log_type: str = "progress"


@router.get("/projects/{project_id}/logs")
def list_project_logs(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取项目进展/笔记记录。"""
    project = db.query(ProjectRecord).filter(
        ProjectRecord.id == project_id, ProjectRecord.user_id == user.id,
    ).first()
    if not project:
        raise HTTPException(404, "项目不存在")
    logs = (
        db.query(ProjectLog)
        .filter(ProjectLog.project_id == project_id)
        .order_by(ProjectLog.created_at.desc())
        .all()
    )
    return {"logs": [_serialize_log(l) for l in logs]}


def _serialize_log(l: ProjectLog) -> dict:
    return {
        "id": l.id,
        "content": l.content,
        "reflection": getattr(l, 'reflection', None),
        "task_status": getattr(l, 'task_status', 'done'),
        "log_type": getattr(l, 'log_type', 'progress'),
        "created_at": l.created_at.isoformat(),
    }


@router.post("/projects/{project_id}/logs", status_code=201)
def create_project_log(
    project_id: int,
    req: CreateProjectLogRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """添加项目进展/笔记记录。"""
    project = db.query(ProjectRecord).filter(
        ProjectRecord.id == project_id, ProjectRecord.user_id == user.id,
    ).first()
    if not project:
        raise HTTPException(404, "项目不存在")
    if not req.content.strip():
        raise HTTPException(400, "内容不能为空")
    log = ProjectLog(
        project_id=project_id,
        content=req.content.strip(),
        reflection=req.reflection.strip() if req.reflection else None,
        task_status=req.task_status,
        log_type=req.log_type,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return _serialize_log(log)


class UpdateProjectLogRequest(BaseModel):
    content: Optional[str] = None
    reflection: Optional[str] = None
    task_status: Optional[str] = None


@router.patch("/projects/{project_id}/logs/{log_id}")
def update_project_log(
    project_id: int,
    log_id: int,
    req: UpdateProjectLogRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新项目进展记录。"""
    project = db.query(ProjectRecord).filter(
        ProjectRecord.id == project_id, ProjectRecord.user_id == user.id,
    ).first()
    if not project:
        raise HTTPException(404, "项目不存在")
    log = db.query(ProjectLog).filter(ProjectLog.id == log_id, ProjectLog.project_id == project_id).first()
    if not log:
        raise HTTPException(404, "记录不存在")
    if req.content is not None:
        log.content = req.content
    if req.reflection is not None:
        log.reflection = req.reflection or None
    if req.task_status is not None:
        log.task_status = req.task_status
    db.commit()
    db.refresh(log)
    return _serialize_log(log)


@router.delete("/projects/{project_id}/logs/{log_id}", status_code=204)
def delete_project_log(
    project_id: int,
    log_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除项目进展记录。"""
    project = db.query(ProjectRecord).filter(
        ProjectRecord.id == project_id, ProjectRecord.user_id == user.id,
    ).first()
    if not project:
        raise HTTPException(404, "项目不存在")
    log = db.query(ProjectLog).filter(ProjectLog.id == log_id, ProjectLog.project_id == project_id).first()
    if not log:
        raise HTTPException(404, "记录不存在")
    db.delete(log)
    db.commit()


# ── Interviews ────────────────────────────────────────────────────────────────

@router.get("/interviews")
def list_interviews(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    interviews = (
        db.query(InterviewRecord)
        .filter(InterviewRecord.user_id == user.id)
        .order_by(InterviewRecord.created_at.desc())
        .all()
    )
    return {"interviews": [_serialize_interview(i) for i in interviews]}


@router.post("/interviews", status_code=201)
def create_interview(
    req: CreateInterviewRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建面试记录（不自动生成 AI 复盘，用户手动触发）。"""
    profile_id = _get_profile_id(user, db)

    interview_at = None
    if req.interview_at:
        try:
            interview_at = datetime.fromisoformat(req.interview_at)
        except ValueError:
            pass

    record = InterviewRecord(
        user_id=user.id,
        profile_id=profile_id,
        application_id=req.application_id,
        company=req.company,
        position=req.position,
        round=req.round,
        content_summary=req.content_summary,
        self_rating=req.self_rating,
        result=req.result,
        reflection=req.reflection,
        ai_analysis=None,
        interview_at=interview_at or datetime.now(timezone.utc),
    )
    db.add(record)
    db.flush()
    db.commit()
    db.refresh(record)
    return _serialize_interview(record)


@router.patch("/interviews/{interview_id}")
def update_interview(
    interview_id: int,
    req: UpdateInterviewRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(InterviewRecord).filter(
        InterviewRecord.id == interview_id,
        InterviewRecord.user_id == user.id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="面试记录不存在")

    if req.result is not None:
        record.result = req.result
    if req.reflection is not None:
        record.reflection = req.reflection
    if req.self_rating is not None:
        record.self_rating = req.self_rating

    db.commit()
    db.refresh(record)
    return _serialize_interview(record)


@router.post("/interviews/{interview_id}/analyze")
def analyze_interview(
    interview_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """用户手动触发 AI 复盘分析。"""
    record = db.query(InterviewRecord).filter(
        InterviewRecord.id == interview_id,
        InterviewRecord.user_id == user.id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="面试记录不存在")

    profile_id = _get_profile_id(user, db)
    profile_skills = _get_profile_skills(profile_id, db)

    ai_analysis = generate_interview_analysis(
        company=record.company,
        position=record.position,
        round_=record.round,
        content_summary=record.content_summary,
        self_rating=record.self_rating,
        profile_skills=profile_skills,
    )
    record.ai_analysis = ai_analysis
    db.commit()
    db.refresh(record)
    return _serialize_interview(record)


@router.delete("/interviews/{interview_id}", status_code=204)
def delete_interview(
    interview_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(InterviewRecord).filter(
        InterviewRecord.id == interview_id,
        InterviewRecord.user_id == user.id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="面试记录不存在")
    db.delete(record)
    db.commit()


def _serialize_interview(i: InterviewRecord) -> dict:
    ai = None
    if i.ai_analysis:
        try:
            ai = json.loads(i.ai_analysis)
        except Exception:
            ai = None

    return {
        "id": i.id,
        "company": i.company,
        "position": i.position,
        "round": i.round,
        "content_summary": i.content_summary,
        "self_rating": i.self_rating,
        "result": i.result,
        "reflection": i.reflection,
        "ai_analysis": ai,
        "application_id": i.application_id,
        "interview_at": i.interview_at.isoformat() if i.interview_at else None,
        "created_at": i.created_at.isoformat(),
    }


# ── Learning Notes ───────────────────────────────────────────────────────────

class CreateLearningNoteRequest(BaseModel):
    title: str
    summary: str = ""
    tags: list[str] = []
    linked_skill: Optional[str] = None


class UpdateLearningNoteRequest(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[list[str]] = None
    linked_skill: Optional[str] = None


@router.get("/learning-notes")
def list_learning_notes(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户所有学习记录。"""
    notes = (
        db.query(LearningNote)
        .filter(LearningNote.user_id == user.id)
        .order_by(LearningNote.created_at.desc())
        .all()
    )
    return {"notes": [_serialize_note(n) for n in notes]}


@router.post("/learning-notes", status_code=201)
def create_learning_note(
    req: CreateLearningNoteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建学习记录。"""
    if not req.title.strip():
        raise HTTPException(400, "标题不能为空")
    profile_id = _get_profile_id(user, db)
    note = LearningNote(
        user_id=user.id,
        profile_id=profile_id,
        title=req.title.strip(),
        summary=req.summary.strip(),
        tags=req.tags,
        linked_skill=req.linked_skill.strip() if req.linked_skill else None,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return _serialize_note(note)


@router.patch("/learning-notes/{note_id}")
def update_learning_note(
    note_id: int,
    req: UpdateLearningNoteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新学习记录。"""
    note = db.query(LearningNote).filter(
        LearningNote.id == note_id,
        LearningNote.user_id == user.id,
    ).first()
    if not note:
        raise HTTPException(404, "学习记录不存在")
    if req.title is not None:
        note.title = req.title.strip()
    if req.summary is not None:
        note.summary = req.summary.strip()
    if req.tags is not None:
        note.tags = req.tags
    if req.linked_skill is not None:
        note.linked_skill = req.linked_skill.strip() or None
    db.commit()
    db.refresh(note)
    return _serialize_note(note)


@router.delete("/learning-notes/{note_id}", status_code=204)
def delete_learning_note(
    note_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除学习记录。"""
    note = db.query(LearningNote).filter(
        LearningNote.id == note_id,
        LearningNote.user_id == user.id,
    ).first()
    if not note:
        raise HTTPException(404, "学习记录不存在")
    db.delete(note)
    db.commit()


def _serialize_note(n: LearningNote) -> dict:
    return {
        "id": n.id,
        "title": n.title,
        "summary": n.summary,
        "tags": n.tags or [],
        "linked_skill": n.linked_skill,
        "created_at": n.created_at.isoformat(),
    }
