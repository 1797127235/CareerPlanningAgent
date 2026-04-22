"""成长档案路由 — 项目记录 / 求职追踪。"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from backend.auth import get_current_user
from backend.db import get_db
from backend.models import (
    ActionPlanV2,
    ActionProgress,
    CareerGoal,
    GrowthEntry,
    InterviewRecord,
    JDDiagnosis,
    JobApplication,
    Profile,
    ProjectLog,
    ProjectRecord,
    User,
)
from backend.services.growth.service import (
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
    stage: str = "applied"             # applied | written_test | interviewing | offered | rejected
    reflection: Optional[str] = None
    interview_at: Optional[str] = None
    application_id: Optional[int] = None


class UpdateInterviewRequest(BaseModel):
    result: Optional[str] = None
    reflection: Optional[str] = None
    self_rating: Optional[str] = None
    stage: Optional[str] = None
    content_summary: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    round: Optional[str] = None


# ── Timeline ──────────────────────────────────────────────────────────────────

@router.get("/dashboard")
def get_growth_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取成长看板数据：目标方向 + 分层技能覆盖率 + 匹配度曲线。"""
    from backend.models import CareerGoal, GrowthSnapshot
    from backend.services.graph import GraphService
    from backend.services.growth.service import _skill_matches

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


# ── Insights ──────────────────────────────────────────────────────────────────

@router.get("/insights")
def get_growth_insights(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """聚合成长洞察卡片数据 — 从各业务表自动拉取，不依赖手动输入。"""
    from sqlalchemy import func

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    profile_id = profile.id if profile else None

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    insights: list[dict] = []

    # ── 1. 近期活跃度 ──
    activity_counts: dict[str, int] = {}
    if profile_id:
        activity_counts["jd"] = (
            db.query(func.count(JDDiagnosis.id))
            .filter(JDDiagnosis.profile_id == profile_id, JDDiagnosis.created_at >= week_ago)
            .scalar() or 0
        )
        activity_counts["project"] = (
            db.query(func.count(ProjectRecord.id))
            .filter(ProjectRecord.profile_id == profile_id, ProjectRecord.created_at >= week_ago)
            .scalar() or 0
        )
        activity_counts["entry"] = (
            db.query(func.count(GrowthEntry.id))
            .filter(GrowthEntry.user_id == user.id, GrowthEntry.created_at >= week_ago)
            .scalar() or 0
        )
    activity_counts["application"] = (
        db.query(func.count(JobApplication.id))
        .filter(JobApplication.user_id == user.id, JobApplication.created_at >= week_ago)
        .scalar() or 0
    )
    activity_counts["interview"] = (
        db.query(func.count(InterviewRecord.id))
        .filter(InterviewRecord.user_id == user.id, InterviewRecord.created_at >= week_ago)
        .scalar() or 0
    )

    total_activity = sum(activity_counts.values())
    if total_activity > 0:
        parts = []
        if activity_counts.get("jd", 0) > 0:
            parts.append(f"{activity_counts['jd']} 次诊断")
        if activity_counts.get("project", 0) > 0:
            parts.append(f"{activity_counts['project']} 个项目")
        if activity_counts.get("application", 0) > 0:
            parts.append(f"{activity_counts['application']} 次投递")
        if activity_counts.get("interview", 0) > 0:
            parts.append(f"{activity_counts['interview']} 场面试")
        if activity_counts.get("entry", 0) > 0:
            parts.append(f"{activity_counts['entry']} 条记录")
        headline = f"最近 7 天：{', '.join(parts)}"
        level = "normal"
    else:
        headline = "最近 7 天没有活动记录"
        level = "warning"

    insights.append({
        "type": "activity",
        "level": level,
        "icon": "activity",
        "headline": headline,
        "detail": "",
        "link": "/growth-log",
    })

    # ── 2. 求职管道 ──
    if user.id:
        interviewing_count = (
            db.query(func.count(JobApplication.id))
            .filter(
                JobApplication.user_id == user.id,
                JobApplication.status.in_(["screening", "scheduled", "interviewed"]),
            )
            .scalar() or 0
        )
        pending_debrief = (
            db.query(func.count(InterviewRecord.id))
            .filter(
                InterviewRecord.user_id == user.id,
                InterviewRecord.result == "pending",
            )
            .scalar() or 0
        )
        if interviewing_count > 0 or pending_debrief > 0:
            parts = []
            if interviewing_count > 0:
                parts.append(f"{interviewing_count} 家在流程中")
            if pending_debrief > 0:
                parts.append(f"{pending_debrief} 场待复盘")
            insights.append({
                "type": "pipeline",
                "level": "highlight" if interviewing_count > 0 else "normal",
                "icon": "briefcase",
                "headline": "求职进展：" + "，".join(parts),
                "detail": "",
                "link": "/pursuits",
            })

    # ── 3. 计划状态 ──
    pending_plans = (
        db.query(GrowthEntry)
        .filter(
            GrowthEntry.user_id == user.id,
            GrowthEntry.is_plan == True,
            GrowthEntry.status == "pending",
        )
        .all()
    )
    if pending_plans:
        overdue = [p for p in pending_plans if p.due_at and p.due_at < now]
        headline = f"{len(pending_plans)} 条待完成计划"
        detail = f"其中 {len(overdue)} 条已逾期" if overdue else ""
        insights.append({
            "type": "plan",
            "level": "warning" if overdue else "normal",
            "icon": "check-circle",
            "headline": headline,
            "detail": detail,
            "link": "/growth-log?filter=plan",
        })

    # ── 4. 最近诊断 ──
    if profile_id:
        latest_jd = (
            db.query(JDDiagnosis)
            .filter(JDDiagnosis.profile_id == profile_id)
            .order_by(JDDiagnosis.created_at.desc())
            .first()
        )
        if latest_jd:
            match = latest_jd.match_score or 0
            try:
                result = json.loads(latest_jd.result_json or "{}")
                gap_skills = result.get("gap_skills", [])[:3]
            except Exception:
                gap_skills = []
            detail = f"缺口：{', '.join(gap_skills)}" if gap_skills else ""
            insights.append({
                "type": "diagnosis",
                "level": "normal",
                "icon": "target",
                "headline": f"最近诊断：{latest_jd.jd_title or '未命名岗位'} · 匹配度 {match}%",
                "detail": detail,
                "link": "/jd-diagnosis",
            })

    # ── 5. 最近面试 ──
    latest_interview = (
        db.query(InterviewRecord)
        .filter(InterviewRecord.user_id == user.id)
        .order_by(InterviewRecord.interview_at.desc())
        .first()
    )
    if latest_interview:
        rating_map = {"good": "发挥好", "medium": "一般", "bad": "发挥差"}
        rating = rating_map.get(latest_interview.self_rating or "", "")
        headline = f"最近面试：{latest_interview.company or '未知公司'} {latest_interview.round or ''}"
        if rating:
            headline += f" · {rating}"
        # AI 分析中的第一条建议
        detail = ""
        if latest_interview.ai_analysis:
            actions = latest_interview.ai_analysis.get("action_items", [])
            if actions:
                detail = f"Coach 建议：{actions[0]}"
        insights.append({
            "type": "interview",
            "level": "highlight" if latest_interview.self_rating == "good" else "normal",
            "icon": "mic",
            "headline": headline,
            "detail": detail,
            "link": "/growth-log",
        })

    return {"insights": insights}


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
    db.query(ProjectLog).filter(ProjectLog.project_id == project_id).delete()
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
        stage=req.stage,
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
    if req.stage is not None:
        record.stage = req.stage
    if req.content_summary is not None:
        record.content_summary = req.content_summary
    if req.company is not None:
        record.company = req.company
    if req.position is not None:
        record.position = req.position
    if req.round is not None:
        record.round = req.round

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


class SuggestAnswerRequest(BaseModel):
    question: str
    answer: str


@router.post("/interviews/{interview_id}/suggest-answer")
def suggest_answer_for_question(
    interview_id: int,
    req: SuggestAnswerRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """对单道面试题的回答给出 AI 改进建议。"""
    record = db.query(InterviewRecord).filter(
        InterviewRecord.id == interview_id,
        InterviewRecord.user_id == user.id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="面试记录不存在")

    if not req.question.strip():
        raise HTTPException(status_code=400, detail="题目不能为空")

    system_prompt = (
        "你是一位资深技术面试官与面试教练。"
        "用户会提供一道面试题和他的回答，你需要给出针对性的改进建议。"
        "输出结构必须严格遵循以下 JSON 格式，不要添加任何额外字段或 markdown 代码块标记：\n"
        "{\n"
        '  "score": <1-10 的整数评分>,\n'
        '  "strengths": [<回答的亮点，1-2 条>],\n'
        '  "weaknesses": [<回答的不足，1-3 条>],\n'
        '  "suggested_answer": <一段优化后的示范回答，100-200 字>\n'
        "}"
    )

    user_prompt = (
        f"面试岗位：{record.position or '未指定'}\n"
        f"面试轮次：{record.round or '未指定'}\n\n"
        f"【题目】\n{req.question}\n\n"
        f"【用户回答】\n{req.answer or '（未填写）'}\n\n"
        f"请给出 JSON 格式的改进建议。"
    )

    try:
        from backend.llm import get_llm_client, get_model
        resp = get_llm_client(timeout=45).chat.completions.create(
            model=get_model("fast"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
            max_tokens=1200,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
    except Exception as e:
        logger.warning("suggest-answer LLM failed: %s", e)
        raise HTTPException(status_code=500, detail="AI 建议生成失败，请稍后重试")

    return result


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
        "stage": i.stage,
        "reflection": i.reflection,
        "ai_analysis": ai,
        "application_id": i.application_id,
        "interview_at": i.interview_at.isoformat() if i.interview_at else None,
        "created_at": i.created_at.isoformat(),
    }


# ── GrowthEntry v2: 统一记录 ────────────────────────────────────────

class GrowthEntryCreate(BaseModel):
    content: str
    category: str | None = None
    tags: list[str] = []
    structured_data: dict | None = None
    is_plan: bool = False
    due_type: str | None = None
    due_at: datetime | None = None
    linked_project_id: int | None = None
    linked_application_id: int | None = None
    model_config = {"extra": "ignore"}


class GrowthEntryUpdate(BaseModel):
    content: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    structured_data: dict | None = None
    status: str | None = None         # done|pending|dropped
    due_type: str | None = None
    due_at: datetime | None = None
    model_config = {"extra": "ignore"}


@router.get("/entries")
def list_entries(
    status: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列表。默认倒序按 created_at。"""
    q = db.query(GrowthEntry).filter(GrowthEntry.user_id == user.id)
    if status:
        q = q.filter(GrowthEntry.status == status)
    if category:
        q = q.filter(GrowthEntry.category == category)
    if tag:
        # tags 是 JSON，SQLite 里用 LIKE（不做严格匹配，demo 级够用）
        q = q.filter(GrowthEntry.tags.like(f'%"{tag}"%'))
    entries = q.order_by(GrowthEntry.created_at.desc()).limit(200).all()
    return {"entries": [_entry_to_dict(e) for e in entries]}


@router.post("/entries", status_code=201)
def create_entry(
    req: GrowthEntryCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    entry = GrowthEntry(
        user_id=user.id,
        content=req.content,
        category=req.category,
        tags=req.tags,
        structured_data=req.structured_data,
        is_plan=req.is_plan,
        status="pending" if req.is_plan else "done",
        due_type=req.due_type,
        due_at=req.due_at,
        linked_project_id=req.linked_project_id,
        linked_application_id=req.linked_application_id,
        completed_at=None if req.is_plan else now,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _entry_to_dict(entry)


@router.patch("/entries/{entry_id}")
def update_entry(
    entry_id: int,
    req: GrowthEntryUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = db.query(GrowthEntry).filter(
        GrowthEntry.id == entry_id, GrowthEntry.user_id == user.id
    ).first()
    if not entry:
        raise HTTPException(404, "记录不存在")

    data = req.model_dump(exclude_none=True)
    # 状态改成 done 时自动设 completed_at
    if data.get("status") == "done" and entry.status != "done":
        entry.completed_at = datetime.now(timezone.utc)
    for k, v in data.items():
        setattr(entry, k, v)
    db.commit()
    db.refresh(entry)
    return _entry_to_dict(entry)


@router.delete("/entries/{entry_id}", status_code=204)
def delete_entry(
    entry_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = db.query(GrowthEntry).filter(
        GrowthEntry.id == entry_id, GrowthEntry.user_id == user.id
    ).first()
    if not entry:
        raise HTTPException(404, "记录不存在")
    db.delete(entry)
    db.commit()


@router.post("/entries/{entry_id}/ai-suggest")
def ai_suggest(
    entry_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from backend.skills import invoke_skill
    from backend.models import CareerGoal

    entry = db.query(GrowthEntry).filter(
        GrowthEntry.id == entry_id, GrowthEntry.user_id == user.id
    ).first()
    if not entry:
        raise HTTPException(404, "记录不存在")

    # 取画像 + 目标
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    goal = db.query(CareerGoal).filter(
        CareerGoal.user_id == user.id, CareerGoal.is_active == True
    ).first()

    profile_data = json.loads(profile.profile_json or "{}") if profile else {}
    user_skills = [s.get("name", "") for s in profile_data.get("skills", []) if s.get("name")]

    try:
        result = invoke_skill(
            "growth-suggest",
            target_label=goal.target_label if goal else "未选方向",
            user_skills=", ".join(user_skills[:20]) or "无",
            entry_category=entry.category or "note",
            entry_content=entry.content,
            structured_data=json.dumps(entry.structured_data or {}, ensure_ascii=False),
        )
        suggestions = result.get("suggestions", []) if isinstance(result, dict) else []
    except Exception as e:
        logger.warning("ai-suggest failed: %s", e)
        suggestions = []

    # 写回 entry
    entry.ai_suggestions = suggestions
    db.commit()
    return {"suggestions": suggestions}


def _entry_to_dict(e: GrowthEntry) -> dict:
    return {
        "id": e.id,
        "content": e.content,
        "category": e.category,
        "tags": e.tags or [],
        "structured_data": e.structured_data,
        "is_plan": e.is_plan,
        "status": e.status,
        "due_type": e.due_type,
        "due_at": e.due_at.isoformat() if e.due_at else None,
        "ai_suggestions": e.ai_suggestions,
        "linked_project_id": e.linked_project_id,
        "linked_application_id": e.linked_application_id,
        "completed_at": e.completed_at.isoformat() if e.completed_at else None,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }

