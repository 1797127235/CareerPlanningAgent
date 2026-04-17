"""Mock interview router — generate questions, submit answers, get evaluation."""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import get_db
from backend.db_models import MockInterview, InterviewRecord, Profile, User

router = APIRouter()
logger = logging.getLogger(__name__)


def _build_profile_summary(profile_data: dict) -> str:
    """Build a concise profile summary string for LLM prompts."""
    parts = []

    edu = profile_data.get("education", {})
    if edu:
        parts.append(f"教育：{edu.get('school', '')} {edu.get('major', '')} {edu.get('degree', '')}")

    skills = profile_data.get("skills", [])
    if skills:
        skill_names = [s["name"] if isinstance(s, dict) else str(s) for s in skills[:15]]
        parts.append(f"技能：{', '.join(skill_names)}")

    projects = profile_data.get("projects", [])
    if projects:
        proj_lines = []
        for p in projects[:5]:
            if isinstance(p, str):
                proj_lines.append(f"- {p[:100]}")
            elif isinstance(p, dict):
                proj_lines.append(f"- {p.get('name', '')}: {p.get('description', '')[:100]}")
        parts.append("项目经历：\n" + "\n".join(proj_lines))

    internships = profile_data.get("internships", [])
    if internships:
        intern_lines = []
        for it in internships[:3]:
            if isinstance(it, dict):
                intern_lines.append(f"- {it.get('company', '')} {it.get('role', '')}：{it.get('highlights', '')[:80]}")
        if intern_lines:
            parts.append("实习经历：\n" + "\n".join(intern_lines))

    return "\n\n".join(parts) if parts else "（画像信息较少）"


class StartRequest(BaseModel):
    target_role: str
    jd_text: str = ""


@router.post("/start")
def start_interview(
    req: StartRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate interview questions and create a new mock interview session."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(404, "请先上传简历建立画像")

    profile_data = json.loads(profile.profile_json or "{}")
    profile_summary = _build_profile_summary(profile_data)

    from backend.skills import invoke_skill
    questions = invoke_skill(
        "mock-interview-gen",
        target_role=req.target_role,
        jd_requirements=req.jd_text[:2000] if req.jd_text else "（未提供 JD，请根据岗位名称和候选人画像出题）",
        profile_summary=profile_summary,
    )

    # Ensure it's a list
    if not isinstance(questions, list):
        raise HTTPException(500, "题目生成失败，请重试")

    row = MockInterview(
        user_id=user.id,
        target_role=req.target_role,
        jd_text=req.jd_text[:5000] if req.jd_text else "",
        questions_json=json.dumps(questions, ensure_ascii=False),
        status="created",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "id": row.id,
        "target_role": row.target_role,
        "questions": questions,
    }


class SubmitRequest(BaseModel):
    answers: list[dict]  # [{question_id: "q1", answer: "..."}]


@router.post("/{interview_id}/submit")
def submit_answers(
    interview_id: int,
    req: SubmitRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit answers and get AI evaluation."""
    row = (
        db.query(MockInterview)
        .filter(MockInterview.id == interview_id, MockInterview.user_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(404, "面试记录不存在")
    if row.status == "evaluated":
        # Return cached evaluation
        return json.loads(row.evaluation_json or "{}")

    row.answers_json = json.dumps(req.answers, ensure_ascii=False)
    row.status = "in_progress"
    db.commit()

    # Build Q&A pairs for evaluation
    questions = json.loads(row.questions_json or "[]")
    answer_map = {a["question_id"]: a["answer"] for a in req.answers}

    qa_lines = []
    for q in questions:
        qid = q["id"]
        qa_lines.append(f"【题目 {qid}】({q.get('type', '')}) {q['question']}")
        qa_lines.append(f"【回答】{answer_map.get(qid, '（未作答）')}")
        qa_lines.append("")

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    profile_data = json.loads(profile.profile_json or "{}") if profile else {}
    profile_summary = _build_profile_summary(profile_data)

    from backend.skills import invoke_skill
    evaluation = invoke_skill(
        "mock-interview-eval",
        target_role=row.target_role,
        profile_summary=profile_summary,
        qa_pairs="\n".join(qa_lines),
    )

    if not isinstance(evaluation, dict):
        raise HTTPException(500, "评估生成失败，请重试")

    row.evaluation_json = json.dumps(evaluation, ensure_ascii=False)
    row.status = "evaluated"

    # ── 接入成长档案：创建 InterviewRecord ──
    overall_score = evaluation.get("overall_score", 0)
    summary = evaluation.get("summary", evaluation.get("overall_comment", ""))
    skill_gaps = evaluation.get("skill_gaps", [])
    tips = evaluation.get("tips", [])

    # 自评等级：>=80 good, >=60 medium, <60 bad
    if overall_score >= 80:
        self_rating = "good"
    elif overall_score >= 60:
        self_rating = "medium"
    else:
        self_rating = "bad"

    # 内容摘要：列出题目类型和考察方向
    questions = json.loads(row.questions_json or "[]")
    q_summary_parts = []
    for q in questions:
        q_type = {"technical": "技术题", "behavioral": "行为题", "scenario": "场景题"}.get(q.get("type", ""), q.get("type", ""))
        q_summary_parts.append(f"{q_type}·{q.get('focus_area', '')}")
    content_summary = f"AI 模拟面试（{row.target_role}）：{' / '.join(q_summary_parts)}，综合得分 {overall_score}"

    # AI 分析 JSON：包含完整评估结果
    ai_analysis_data = {
        "source": "mock_interview",
        "mock_interview_id": row.id,
        "overall_score": overall_score,
        "summary": summary,
        "skill_gaps": skill_gaps,
        "tips": tips,
        "per_question_scores": [
            {"question_id": r.get("question_id", ""), "score": r.get("score", 0)}
            for r in evaluation.get("reviews", evaluation.get("per_question", []))
        ],
    }

    interview_record = InterviewRecord(
        user_id=user.id,
        profile_id=profile.id if profile else None,
        company="AI 模拟",
        position=row.target_role,
        round="模拟面试",
        content_summary=content_summary,
        self_rating=self_rating,
        result="passed" if overall_score >= 60 else "failed",
        stage="interviewing",
        reflection=summary,
        ai_analysis=json.dumps(ai_analysis_data, ensure_ascii=False),
    )
    db.add(interview_record)
    db.commit()

    return evaluation


@router.get("/history")
def list_interviews(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List past mock interviews."""
    rows = (
        db.query(MockInterview)
        .filter(MockInterview.user_id == user.id)
        .order_by(MockInterview.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": r.id,
            "target_role": r.target_role,
            "status": r.status,
            "score": json.loads(r.evaluation_json or "{}").get("overall_score") if r.evaluation_json else None,
            "created_at": str(r.created_at),
        }
        for r in rows
    ]


@router.get("/{interview_id}")
def get_interview(
    interview_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single mock interview with all data."""
    row = (
        db.query(MockInterview)
        .filter(MockInterview.id == interview_id, MockInterview.user_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(404, "面试记录不存在")

    return {
        "id": row.id,
        "target_role": row.target_role,
        "status": row.status,
        "questions": json.loads(row.questions_json or "[]"),
        "answers": json.loads(row.answers_json or "[]"),
        "evaluation": json.loads(row.evaluation_json or "{}") if row.evaluation_json else None,
        "created_at": str(row.created_at),
    }


@router.delete("/{interview_id}")
def delete_interview(
    interview_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a mock interview record."""
    row = (
        db.query(MockInterview)
        .filter(MockInterview.id == interview_id, MockInterview.user_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(404, "面试记录不存在")
    db.delete(row)
    db.commit()
    return {"success": True}
