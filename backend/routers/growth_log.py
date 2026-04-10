"""成长档案路由 — 项目记录 / 面试记录 / 事件时间线。"""
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
    GrowthEvent,
    InterviewRecord,
    Profile,
    ProjectLog,
    ProjectRecord,
    User,
)
from backend.services.growth_log_service import (
    create_growth_event,
    generate_interview_analysis,
    get_monthly_summary,
    get_timeline,
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
    github_url: Optional[str] = None
    status: str = "in_progress"        # planning | in_progress | completed
    linked_node_id: Optional[str] = None
    reflection: Optional[str] = None
    started_at: Optional[str] = None


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    skills_used: Optional[list[str]] = None
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

@router.get("/timeline")
def get_growth_timeline(
    event_type: Optional[str] = None,
    limit: int = 30,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取成长事件时间线。"""
    profile_id = _get_profile_id(user, db)
    events = get_timeline(
        user_id=user.id,
        profile_id=profile_id,
        event_type=event_type,
        limit=limit,
        offset=offset,
        db=db,
    )
    return {"events": events, "total": len(events)}


@router.get("/summary")
def get_growth_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取本月成长摘要。"""
    profile_id = _get_profile_id(user, db)
    return get_monthly_summary(user_id=user.id, profile_id=profile_id, db=db)


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
        github_url=req.github_url,
        status=req.status,
        linked_node_id=req.linked_node_id,
        reflection=req.reflection,
        started_at=started_at or datetime.now(timezone.utc),
        completed_at=completed_at,
    )
    db.add(project)
    db.flush()

    # 任何状态都创建成长事件（用户需要看到记录）
    _trigger_project_event(project, user.id, profile_id, db)

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
    """更新项目记录。状态变为 completed 时自动触发成长事件。"""
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

    # 刚完成 → 触发成长事件
    if req.status == "completed" and prev_status != "completed":
        profile_id = project.profile_id or _get_profile_id(user, db)
        _trigger_project_event(project, user.id, profile_id, db)

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
    # 级联删除关联的 GrowthEvent
    db.query(GrowthEvent).filter(
        GrowthEvent.source_table == "project_records",
        GrowthEvent.source_id == project_id,
    ).delete()
    db.delete(project)
    db.commit()


def _trigger_project_event(project: ProjectRecord, user_id: int, profile_id: int | None, db: Session):
    """项目创建/完成时创建 GrowthEvent。"""
    skills_list = project.skills_used or []
    status_label = {"planning": "规划", "in_progress": "开始", "completed": "完成"}.get(project.status, "记录")
    summary = f"{status_label}项目「{project.name}」"
    if skills_list:
        summary += f" · 技能: {', '.join(skills_list[:3])}"

    create_growth_event(
        user_id=user_id,
        profile_id=profile_id,
        event_type="project_completed",
        source_table="project_records",
        source_id=project.id,
        summary=summary,
        skills_delta={"added": skills_list},
        db=db,
    )


def _serialize_project(p: ProjectRecord) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "skills_used": p.skills_used or [],
        "github_url": p.github_url,
        "status": p.status,
        "linked_node_id": p.linked_node_id,
        "reflection": p.reflection,
        "started_at": p.started_at.isoformat() if p.started_at else None,
        "completed_at": p.completed_at.isoformat() if p.completed_at else None,
        "created_at": p.created_at.isoformat(),
    }


# ── Project Logs ─────────────────────────────────────────────────────────────

class CreateProjectLogRequest(BaseModel):
    content: str
    log_type: str = "progress"  # progress | note


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
    return {"logs": [{"id": l.id, "content": l.content, "log_type": getattr(l, 'log_type', 'progress'), "created_at": l.created_at.isoformat()} for l in logs]}


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
    log = ProjectLog(project_id=project_id, content=req.content.strip(), log_type=req.log_type)
    db.add(log)
    db.commit()
    db.refresh(log)
    return {"id": log.id, "content": log.content, "log_type": log.log_type, "created_at": log.created_at.isoformat()}


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

    # 创建成长事件
    rating_label = {"good": "发挥不错", "medium": "正常发挥", "bad": "发挥一般"}.get(req.self_rating, "")
    summary = f"{req.company} {req.round}"
    if rating_label:
        summary += f" · {rating_label}"

    create_growth_event(
        user_id=user.id,
        profile_id=profile_id,
        event_type="interview_done",
        source_table="interview_records",
        source_id=record.id,
        summary=summary,
        db=db,
    )

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
    # 级联删除关联的 GrowthEvent
    db.query(GrowthEvent).filter(
        GrowthEvent.source_table == "interview_records",
        GrowthEvent.source_id == interview_id,
    ).delete()
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
