"""成长档案路由 — 项目记录 / 求职追踪。"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.auth import get_current_user
from backend.db import get_db
from backend.models import (
    GrowthEntry,
    InterviewRecord,
    Profile,
    ProjectLog,
    ProjectRecord,
    User,
)
from backend.services.growth.dashboard import build_growth_dashboard
from backend.services.growth.insights import build_growth_insights_with_profile
from backend.services.growth.service import generate_interview_analysis

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
    return build_growth_dashboard(user, db)


# ── Insights ──────────────────────────────────────────────────────────────────

@router.get("/insights")
def get_growth_insights(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """聚合成长洞察卡片数据 — 从各业务表自动拉取，不依赖手动输入。"""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    profile_id = profile.id if profile else None
    return build_growth_insights_with_profile(user, db, profile_id)


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

