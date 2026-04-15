"""成长档案路由 — 项目记录 / 求职追踪。"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from backend.auth import get_current_user
from backend.db import get_db
from backend.db_models import (
    ActionPlanV2,
    ActionProgress,
    InterviewRecord,
    Profile,
    ProjectLog,
    ProjectRecord,
    User,
)
from backend.services.growth_log_service import (
    generate_interview_analysis,
)

logger = logging.getLogger(__name__)

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


def _auto_complete_plan_tasks(
    db: Session,
    user_id: int,
    project_name: str | None = None,
    skills: list[str] | None = None,
    record_type: str = "project",
) -> None:
    """Scan active ActionPlanV2 tasks and auto-check matching ones."""
    try:
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()
        if not profile:
            return

        # Find the latest report_key with ActionPlanV2 data
        latest_plan = (
            db.query(ActionPlanV2)
            .filter(ActionPlanV2.profile_id == profile.id)
            .order_by(ActionPlanV2.generated_at.desc())
            .first()
        )
        if not latest_plan:
            return

        report_key = latest_plan.report_key
        plans = (
            db.query(ActionPlanV2)
            .filter(
                ActionPlanV2.profile_id == profile.id,
                ActionPlanV2.report_key == report_key,
            )
            .all()
        )

        progress = (
            db.query(ActionProgress)
            .filter(
                ActionProgress.profile_id == profile.id,
                ActionProgress.report_key == report_key,
            )
            .first()
        )
        if not progress:
            progress = ActionProgress(
                profile_id=profile.id,
                report_key=report_key,
                checked={},
            )
            db.add(progress)
            db.flush()

        changed = False
        for plan in plans:
            content = plan.content if isinstance(plan.content, dict) else json.loads(plan.content or "{}")
            for item in content.get("items", []):
                item_id = item.get("id", "")
                if progress.checked.get(item_id):
                    continue  # already done

                # Match by type
                if record_type == "project" and item.get("type") == "project":
                    progress.checked[item_id] = True
                    changed = True
                elif record_type == "learning" and item.get("type") == "skill" and item.get("sub_type") == "learn":
                    # Check if skill name matches
                    skill_name = item.get("skill_name", "").lower()
                    if skills and any(
                        s.lower() in skill_name or skill_name in s.lower()
                        for s in skills
                    ):
                        progress.checked[item_id] = True
                        changed = True
                elif record_type == "application" and item.get("id", "").startswith("prep_apply"):
                    progress.checked[item_id] = True
                    changed = True

        if changed:
            flag_modified(progress, "checked")
            db.commit()
    except Exception as e:
        logger.warning("_auto_complete_plan_tasks failed: %s", e)


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

    # Auto-complete matching action plan tasks
    _auto_complete_plan_tasks(
        db, user.id, project_name=req.name, skills=req.skills_used, record_type="project",
    )

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




@router.get("/journey")
def get_goal_journey(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """当前 active goal 的完整旅程：阶段事件 + 关联 records。"""
    from backend.db_models import CareerGoal, GrowthSnapshot, ProjectRecord, JobApplication

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        return {"has_goal": False}

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
        return {"has_goal": False}

    # ── Stage events from GrowthSnapshot ──
    snapshots = (
        db.query(GrowthSnapshot)
        .filter(
            GrowthSnapshot.profile_id == profile.id,
            GrowthSnapshot.target_node_id == goal.target_node_id,
        )
        .order_by(GrowthSnapshot.created_at.asc())
        .all()
    )

    stage_events = [
        {
            "id": s.id,
            "trigger": s.trigger,
            "stage_completed": s.stage_completed,
            "readiness_score": round(s.readiness_score or 0, 1),
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in snapshots
    ]

    # ── Records under this goal (按 goal.set_at 之后) ──
    projects = (
        db.query(ProjectRecord)
        .filter(
            ProjectRecord.profile_id == profile.id,
            ProjectRecord.created_at >= goal.set_at,
        )
        .order_by(ProjectRecord.created_at.asc())
        .all()
    )
    applications = (
        db.query(JobApplication)
        .filter(
            JobApplication.user_id == user.id,
            JobApplication.created_at >= goal.set_at,
        )
        .order_by(JobApplication.created_at.asc())
        .all()
    )

    return {
        "has_goal": True,
        "goal": {
            "id": goal.id,
            "target_node_id": goal.target_node_id,
            "target_label": goal.target_label,
            "set_at": goal.set_at.isoformat() if goal.set_at else None,
        },
        "stage_events": stage_events,
        "projects_under_goal": [
            {
                "id": p.id,
                "name": p.name,
                "status": p.status,
                "created_at": p.created_at.isoformat(),
            }
            for p in projects
        ],
        "applications_under_goal": [
            {
                "id": a.id,
                "company": a.company,
                "position": a.position,
                "status": a.status,
                "created_at": a.created_at.isoformat(),
            }
            for a in applications
        ],
    }


@router.get("/goal-history")
def get_goal_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """所有 career_goal（active + cleared），按 set_at 降序。"""
    from backend.db_models import CareerGoal

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        return {"goals": []}

    goals = (
        db.query(CareerGoal)
        .filter(
            CareerGoal.user_id == user.id,
            CareerGoal.profile_id == profile.id,
        )
        .order_by(CareerGoal.set_at.desc())
        .all()
    )

    return {
        "goals": [
            {
                "id": g.id,
                "target_node_id": g.target_node_id,
                "target_label": g.target_label,
                "is_active": g.is_active,
                "is_primary": g.is_primary,
                "set_at": g.set_at.isoformat() if g.set_at else None,
                "cleared_at": g.cleared_at.isoformat() if g.cleared_at else None,
                "duration_days": (
                    ((g.cleared_at or datetime.now(timezone.utc)) - g.set_at).days
                    if g.set_at else 0
                ),
            }
            for g in goals
        ],
    }


@router.get("/skills-harvest")
def get_skills_harvest(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """本月技能收获：新触达技能 + 所有已积累技能。"""
    from backend.db_models import JobApplication, InterviewRecord

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        return {
            "has_records": False,
            "month_label": datetime.now(timezone.utc).strftime("%Y 年 %m 月").replace(" 0", " "),
            "monthly_record_count": 0,
            "newly_touched_skills": [],
            "all_touched_skills": [],
        }

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    monthly_count = (
        db.query(ProjectRecord).filter(
            ProjectRecord.profile_id == profile.id,
            ProjectRecord.created_at >= month_start,
        ).count()
        + db.query(JobApplication).filter(
            JobApplication.user_id == user.id,
            JobApplication.created_at >= month_start,
        ).count()
        + db.query(InterviewRecord).filter(
            InterviewRecord.user_id == user.id,
            InterviewRecord.created_at >= month_start,
        ).count()
    )

    projects = (
        db.query(ProjectRecord)
        .filter(ProjectRecord.profile_id == profile.id)
        .order_by(ProjectRecord.created_at.asc())
        .all()
    )
    skill_map: dict[str, dict] = {}
    for p in projects:
        for s in (p.skills_used or []):
            s_clean = s.strip()
            if not s_clean:
                continue
            if s_clean not in skill_map:
                skill_map[s_clean] = {"name": s_clean, "first_seen_at": p.created_at, "use_count": 0}
            skill_map[s_clean]["use_count"] += 1

    all_skills = sorted(skill_map.values(), key=lambda x: x["first_seen_at"], reverse=True)
    newly_touched = [s for s in all_skills if s["first_seen_at"] >= month_start]

    return {
        "has_records": monthly_count > 0 or len(all_skills) > 0,
        "month_label": now.strftime("%Y 年 %m 月").replace(" 0", " "),
        "monthly_record_count": monthly_count,
        "newly_touched_skills": [
            {"name": s["name"], "first_seen_at": s["first_seen_at"].isoformat()}
            for s in newly_touched
        ],
        "all_touched_skills": [
            {
                "name": s["name"],
                "first_seen_at": s["first_seen_at"].isoformat(),
                "use_count": s["use_count"],
            }
            for s in all_skills
        ],
    }


@router.get("/activity-pulse")
def get_activity_pulse(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """12 周活动节奏柱 + 连续活跃周数。"""
    from backend.db_models import JobApplication, InterviewRecord

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        return {"current_streak_weeks": 0, "total_records": 0, "weeks": []}

    now = datetime.now(timezone.utc)
    twelve_weeks_ago = now - timedelta(weeks=12)

    projects = db.query(ProjectRecord).filter(
        ProjectRecord.profile_id == profile.id,
        ProjectRecord.created_at >= twelve_weeks_ago,
    ).all()
    applications = db.query(JobApplication).filter(
        JobApplication.user_id == user.id,
        JobApplication.created_at >= twelve_weeks_ago,
    ).all()
    interviews = db.query(InterviewRecord).filter(
        InterviewRecord.user_id == user.id,
        InterviewRecord.created_at >= twelve_weeks_ago,
    ).all()

    bucket: dict[str, dict] = defaultdict(lambda: {"projects": 0, "applications": 0, "interviews": 0})
    for p in projects:
        key = p.created_at.strftime("%G-W%V")
        bucket[key]["projects"] += 1
    for a in applications:
        key = a.created_at.strftime("%G-W%V")
        bucket[key]["applications"] += 1
    for i in interviews:
        key = i.created_at.strftime("%G-W%V")
        bucket[key]["interviews"] += 1

    weeks = []
    for i in range(11, -1, -1):
        wk_date = now - timedelta(weeks=i)
        iso_key = wk_date.strftime("%G-W%V")
        weeks.append({
            "week_label": wk_date.strftime("%m/%d").lstrip("0").replace("/0", "/"),
            "iso_week": iso_key,
            "projects": bucket[iso_key]["projects"],
            "applications": bucket[iso_key]["applications"],
            "interviews": bucket[iso_key]["interviews"],
        })

    streak = 0
    for w in reversed(weeks):
        if (w["projects"] + w["applications"] + w["interviews"]) > 0:
            streak += 1
        else:
            break

    total = sum(w["projects"] + w["applications"] + w["interviews"] for w in weeks)

    return {
        "current_streak_weeks": streak,
        "total_records": total,
        "weeks": weeks,
    }

