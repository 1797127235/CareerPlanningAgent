"""Mock interview router — generate questions, submit answers, get evaluation."""
from __future__ import annotations

import json
import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import get_db
from backend.db_models import (
    CareerGoal,
    JobApplication,
    JDDiagnosis,
    MockInterview,
    InterviewQuestionBank,
    InterviewRecord,
    Profile,
    ProjectRecord,
    Report,
    User,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# 占位符/幻觉模式：XX/YY/ZZ/AA/BB 项目，某项目，某个公司等
_PLACEHOLDER_RE = re.compile(
    r"(?:XX|YY|ZZ|AA|BB|CC|DD|EE|FF|GG|HH|II|JJ|KK|LL|MM|NN|OO|PP|QQ|RR|SS|TT|UU|VV|WW)(?:项目|系统|平台|模块|服务|公司|团队)"
    r"|某项目|某个项目|某系统|某个系统|某平台|某个平台|某模块|某个模块"
    r"|某公司|某个公司|某团队|某个团队|某部门"
    r"|XXX|YYY|ZZZ|AAA|BBB|CCC|该项目|此项目"
    r"|\b[A-Z]{2,}项目\b"
)


def _resolve_skill_id(target_role: str) -> str | None:
    """Map target role name to interview skill_id."""
    role = target_role.lower()
    if any(k in role for k in ["c++", "cpp", "系统开发"]):
        return "cpp-system-dev"
    if any(k in role for k in ["前端", "frontend", "react", "vue", "web"]):
        return "frontend-dev"
    if any(k in role for k in ["java", "后端", "spring", "服务端"]):
        return "java-backend"
    if any(k in role for k in ["算法", "algorithm", "机器学习", "深度学习", "ai"]):
        return "algorithm"
    if any(k in role for k in ["产品", "product", "pm"]):
        return "product-manager"
    if any(k in role for k in ["测试", "test", "qa", "质量"]):
        return "test-development"
    return None


def _resolve_difficulty(profile_data: dict) -> str:
    """Infer difficulty level from profile data."""
    internships = profile_data.get("internships", [])
    projects = profile_data.get("projects", [])
    skills = profile_data.get("skills", [])
    has_experience = bool(internships or projects)
    skill_count = len(skills)

    if has_experience and skill_count > 8:
        return "senior"
    elif has_experience:
        return "mid"
    return "junior"


def _sanitize_questions(questions: list) -> list:
    """Detect and filter out questions containing XX/YY/ZZ placeholders."""
    cleaned = []
    for q in questions:
        text = q.get("question", "")
        if _PLACEHOLDER_RE.search(text):
            logger.warning("Placeholder detected in question, filtering: %s", text[:80])
            continue

        follow_ups = q.get("follow_ups", [])
        clean_follow_ups = []
        for fu in follow_ups:
            # Support both string array and object array formats
            fu_text = fu if isinstance(fu, str) else fu.get("question", "")
            if _PLACEHOLDER_RE.search(fu_text):
                logger.warning("Placeholder detected in follow_up, filtering: %s", fu_text[:80])
                continue
            clean_follow_ups.append(fu)
        q["follow_ups"] = clean_follow_ups
        cleaned.append(q)

    return cleaned


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


def _build_enriched_profile(user_id: int, db: Session) -> dict:
    """Aggregate growth data (projects, goals, reports) into an enriched profile."""
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    profile_data = json.loads(profile.profile_json or "{}") if profile else {}

    # 1. 成长项目（最近 3 个）
    projects = (
        db.query(ProjectRecord)
        .filter(ProjectRecord.user_id == user_id)
        .order_by(ProjectRecord.updated_at.desc())
        .limit(3)
        .all()
    )
    if projects:
        project_lines = []
        for p in projects:
            status_label = {"planning": "计划中", "in_progress": "进行中", "completed": "已完成"}.get(p.status, p.status)
            skills = ", ".join(p.skills_used or [])
            reflection = p.reflection or ""
            desc = p.description or ""
            project_lines.append(
                f"- {p.name}（{status_label}）：技术栈 {skills}。{desc[:120]} {reflection[:120]}"
            )
        profile_data["growth_projects"] = "\n".join(project_lines)

    # 2. 目标方向的 gap 技能（当前激活的目标）
    goal = (
        db.query(CareerGoal)
        .filter(CareerGoal.user_id == user_id, CareerGoal.is_active == True)
        .order_by(CareerGoal.set_at.desc())
        .first()
    )
    if goal:
        if goal.gap_skills:
            profile_data["gap_skills"] = goal.gap_skills
        if goal.target_label:
            profile_data["career_goal_label"] = goal.target_label

    # 3. 最新发展报告的关键结论
    report = (
        db.query(Report)
        .filter(Report.user_id == user_id)
        .order_by(Report.created_at.desc())
        .first()
    )
    if report:
        if report.summary:
            profile_data["report_summary"] = report.summary
        if report.data_json:
            try:
                report_data = json.loads(report.data_json)
                profile_data["skill_coverage"] = report_data.get("skill_coverage", {})
                # 如果 report.summary 为空，尝试从 data_json 中提取 summary
                if not profile_data.get("report_summary"):
                    profile_data["report_summary"] = report_data.get("summary", "")
            except Exception:
                pass

    return profile_data


# ── Empty answer detection ───────────────────────────────────────

# Any answer shorter than this many Chinese chars is considered empty/敷衍
_EMPTY_MIN_CHARS = 15


def _is_empty_answer(answer: str) -> bool:
    """Detect empty or敷衍 answers that deserve 0 points.

    Rules (any match = empty):
    1. Pure whitespace or empty
    2. Less than EMPTY_MIN_CHARS Chinese-char-equivalent length
    3. Contains known empty-answer phrases
    4. Generic AI fluff without substance
    """
    text = (answer or "").strip()
    if not text:
        return True

    # Count Chinese chars as 1, English words as ~1.5 each
    # A reasonable answer should have at least 15 Chinese-char worth of content
    chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    other_chars = len(text) - chinese_chars
    effective_length = chinese_chars + other_chars * 0.6
    if effective_length < _EMPTY_MIN_CHARS:
        return True

    # Known empty-answer phrases (中文 + 英文)
    empty_phrases = [
        "不知道", "不清楚", "不了解", "不会", "没学过", "忘记了", "跳过", "暂无", "待定",
        "不太清楚", "不太了解", "不太会", "没有经验", "没有做过", "没有接触过",
        "i don't know", "i dont know", "not sure", "no idea", "pass", "skip",
        "还没准备好", "准备不足", "不太熟悉", "不太擅长", "没有深入", "没有具体",
        "记不太清", "不太记得", "暂时没有", "目前没有", "尚无",
    ]
    text_lower = text.lower()
    for phrase in empty_phrases:
        if phrase in text_lower:
            # Word-boundary guard: avoid "pass" matching "password", "skip" matching "skip_list"
            import re as _re
            pat = r'(?<![a-z0-9\u4e00-\u9fff])' + _re.escape(phrase) + r'(?![a-z0-9\u4e00-\u9fff])'
            if _re.search(pat, text_lower):
                return True

    # Single-word / very short generic responses
    short_generics = ["嗯", "啊", "哦", "好的", "明白", "了解了", "谢谢", "ok", "yes", "no", "嗯嗯"]
    if text_lower in short_generics:
        return True

    # Generic AI fluff without substance (contains fluff markers but lacks tech keywords)
    fluff_markers = ["综上所述", "总之", "总而言之", "通过以上分析", "总的来说", "整体而言"]
    has_fluff = any(m in text for m in fluff_markers)
    tech_keywords = ["代码", "函数", "类", "接口", "线程", "锁", "内存", "优化", "性能", "bug",
                     "code", "function", "class", "api", "thread", "lock", "memory", "performance",
                     "设计", "架构", "模块", "组件", "系统", "服务", "数据库", "缓存", "队列",
                     "project", "module", "component", "system", "service", "database", "cache"]
    has_tech = any(kw in text_lower for kw in tech_keywords)
    if has_fluff and not has_tech and effective_length < 30:
        return True

    return False


def _force_score_empty_answers(
    evaluation: dict,
    questions: list[dict],
    answer_map: dict[str, str],
) -> dict:
    """Override evaluation scores: empty answers → 0, recalc overall.

    Handles multiple field names (reviews / per_question / question_evaluations).
    """
    # Find the per-question scoring array under any known key
    per_q_key = None
    for key in ("per_question", "reviews", "question_evaluations"):
        if key in evaluation and isinstance(evaluation[key], list):
            per_q_key = key
            break

    if per_q_key is None:
        logger.warning("_force_score_empty_answers: no per-question array found in evaluation")
        return evaluation

    reviews = evaluation[per_q_key]
    empty_count = 0
    for review in reviews:
        qid = review.get("question_id", "")
        idx = None
        for i, q in enumerate(questions):
            if q.get("id") == qid or qid == f"q{i + 1}":
                idx = i
                break
        if idx is None:
            continue

        answer = answer_map.get(questions[idx].get("id", f"q{idx + 1}"), "")
        if _is_empty_answer(answer):
            review["score"] = 0
            review["strengths"] = []
            review["improvements"] = ["未作答或回答无效。该题必须给出具体技术细节、项目经验或代码示例才能得分。"]
            if "suggested_answer" in review:
                review["suggested_answer"] = "请提供具体的技术实现细节、项目场景描述或可量化的成果数据。"
            empty_count += 1

    if reviews:
        total = sum(r.get("score", 0) for r in reviews)
        evaluation["overall_score"] = round(total / len(reviews))

    if empty_count > 0:
        evaluation["summary"] = f"有 {empty_count} 道题未作答或回答无效，整体表现不合格。建议认真准备后再试。"
        evaluation["skill_gaps"] = ["面试准备不足", "需要补充具体项目经验", "技术深度有待加强"]
        evaluation["tips"] = [
            "每道题必须给出具体的技术细节、代码片段或项目场景，不能泛泛而谈",
            "行为题用 STAR 法则：Situation（场景）→ Task（任务）→ Action（行动）→ Result（结果）",
            "技术题至少包含：用了什么技术、为什么选它、遇到什么坑、怎么解决的",
        ]

    return evaluation


class StartRequest(BaseModel):
    target_role: str
    jd_text: str = ""
    question_count: int = 5  # 5 / 10 / 15
    type_distribution: dict[str, int] | None = None  # {"technical": 3, "scenario": 1, "behavioral": 1}


def _normalize_type_distribution(
    question_count: int,
    type_distribution: dict[str, int] | None,
) -> dict[str, int]:
    """Normalize requested type distribution so it always matches question_count."""
    normalized = {
        "technical": max(int((type_distribution or {}).get("technical", 0) or 0), 0),
        "scenario": max(int((type_distribution or {}).get("scenario", 0) or 0), 0),
        "behavioral": max(int((type_distribution or {}).get("behavioral", 0) or 0), 0),
    }

    total = sum(normalized.values())
    if total <= 0:
        normalized["technical"] = question_count
        return normalized

    if total < question_count:
        normalized["technical"] += question_count - total
        return normalized

    overflow = total - question_count
    for key in ("technical", "scenario", "behavioral"):
        if overflow <= 0:
            break
        reducible = min(normalized[key], overflow)
        normalized[key] -= reducible
        overflow -= reducible

    return normalized


def _fetch_weak_skills(user_id: int, db: Session, skill_id: str | None = None) -> list[str]:
    """Query user's historical interview evaluations to find weak skills."""
    rows = (
        db.query(InterviewRecord)
        .filter(
            InterviewRecord.user_id == user_id,
            InterviewRecord.ai_analysis.isnot(None),
        )
        .order_by(InterviewRecord.created_at.desc())
        .limit(10)
        .all()
    )

    skill_gap_counter: dict[str, int] = {}
    for row in rows:
        try:
            data = json.loads(row.ai_analysis or "{}")
            gaps = data.get("skill_gaps", [])
            for gap in gaps:
                skill_gap_counter[gap] = skill_gap_counter.get(gap, 0) + 1
        except Exception:
            continue

    # Return gaps that appeared more than once, sorted by frequency
    weak = sorted(
        [(gap, count) for gap, count in skill_gap_counter.items() if count >= 1],
        key=lambda x: -x[1],
    )
    return [gap for gap, _ in weak[:8]]


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

    # Build enriched profile with growth data
    profile_data = _build_enriched_profile(user.id, db)
    profile_summary = _build_profile_summary(profile_data)
    raw_resume_text = profile_data.get("raw_text", "")
    skill_id = _resolve_skill_id(req.target_role)

    # Improvement B: auto-fill JD from recent job application if user didn't provide one
    jd_text = req.jd_text
    if not jd_text:
        recent_app = (
            db.query(JobApplication)
            .filter(
                JobApplication.user_id == user.id,
                JobApplication.status.in_(["applied", "screening", "scheduled"]),
            )
            .order_by(JobApplication.applied_at.desc())
            .first()
        )
        if recent_app and recent_app.jd_diagnosis_id:
            jd_diag = db.query(JDDiagnosis).filter(JDDiagnosis.id == recent_app.jd_diagnosis_id).first()
            if jd_diag and jd_diag.jd_text:
                jd_text = jd_diag.jd_text[:2000]
                logger.info("Auto-filled JD from application %d for user %d", recent_app.id, user.id)

    # Fetch historical weak skills
    weak_skills = _fetch_weak_skills(user.id, db, skill_id)
    logger.info("User %d weak skills: %s", user.id, weak_skills)

    # Validate question count / normalize requested distribution
    question_count = min(max(req.question_count, 3), 15)
    type_distribution = _normalize_type_distribution(question_count, req.type_distribution)
    wants_non_technical = any(type_distribution.get(key, 0) > 0 for key in ("scenario", "behavioral"))

    def _legacy_generate():
        """Fallback to generic mock-interview-gen skill."""
        from backend.skills import invoke_skill
        return invoke_skill(
            "mock-interview-gen",
            target_role=req.target_role,
            jd_requirements=jd_text[:2000] if jd_text else "（未提供 JD，请根据岗位名称和候选人画像出题）",
            profile_summary=profile_summary,
        )

    questions = None
    if skill_id:
        # ── Step 1: Try question bank first ──
        if wants_non_technical:
            logger.info("Skip question bank for skill=%s because non-technical questions were requested", skill_id)
        else:
            try:
                from sqlalchemy import func
                bank_rows = (
                    db.query(InterviewQuestionBank)
                    .filter(InterviewQuestionBank.skill_id == skill_id)
                    .order_by(func.random())
                    .limit(question_count)
                    .all()
                )
                if len(bank_rows) >= question_count:
                    logger.info("Using question bank for skill=%s, count=%d", skill_id, len(bank_rows))
                    questions = [
                        {
                            "id": f"q{i + 1}",
                            "type": "technical",
                            "category": row.category,
                            "question": row.question,
                            "focus_area": row.focus_area,
                            "difficulty": row.difficulty,
                            "follow_ups": json.loads(row.follow_ups or "[]"),
                        }
                        for i, row in enumerate(bank_rows)
                    ]
                else:
                    logger.info("Question bank has %d items for skill=%s, need LLM supplement", len(bank_rows), skill_id)
            except Exception as exc:
                logger.warning("Question bank query failed: %s", exc)
                bank_rows = []

        # ── Step 2: If bank insufficient, generate via LLM ──
        if questions is None:
            try:
                from backend.services.interview_skill_loader import build_prompt
                system_prompt, user_prompt = build_prompt(
                    skill_id=skill_id,
                    resume_text=profile_summary,
                    raw_resume_text=raw_resume_text,
                    difficulty=_resolve_difficulty(profile_data),
                    question_count=question_count,
                    follow_up_count=2,
                    jd_text=jd_text,
                    profile_data=profile_data,
                    weak_skills=weak_skills,
                    type_distribution=type_distribution,
                )

                from backend.llm import get_llm_client, get_model
                resp = get_llm_client(timeout=120).chat.completions.create(
                    model=get_model("strong"),
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.4,
                    max_tokens=3000,
                )

                raw = resp.choices[0].message.content.strip()
                if raw.startswith("```"):
                    parts = raw.split("```")
                    if len(parts) > 1:
                        raw = parts[1]
                    if raw.startswith("json"):
                        raw = raw[4:]

                questions = json.loads(raw.strip())
                if not isinstance(questions, list) or len(questions) < 3:
                    logger.warning(
                        "Skill-driven returned %s items, falling back to legacy",
                        len(questions) if isinstance(questions, list) else type(questions).__name__,
                    )
                    questions = None
            except Exception as exc:
                logger.error("Skill-driven generation failed, falling back to legacy: %s", exc)
                questions = None

    if questions is None:
        # Fallback to legacy generic skill
        questions = _legacy_generate()

    # Ensure it's a list
    if not isinstance(questions, list):
        raise HTTPException(500, "题目生成失败，请重试")

    questions = _sanitize_questions(questions)

    # If too few after sanitizing, fallback to generic fallback questions
    _FALLBACK_QUESTIONS = [
        {"question": "请描述一个你主导解决的技术难题，分析思路是什么？", "type": "GENERAL", "category": "综合能力", "topic_summary": "技术难题解决", "difficulty": "medium", "follow_ups": ["有哪些备选方案？为什么选这个？", "重来一次哪里会不同？"]},
        {"question": "技术方案选型时通常考虑哪些因素？请举例。", "type": "GENERAL", "category": "综合能力", "topic_summary": "技术方案选型", "difficulty": "medium", "follow_ups": ["有没有选型失误的经历？怎么补救？", "技术栈不统一时如何推动落地？"]},
        {"question": "分享一次处理线上故障的经历，从发现到修复。", "type": "GENERAL", "category": "综合能力", "topic_summary": "线上故障处理", "difficulty": "medium", "follow_ups": ["根因是什么？如何预防？", "你在其中承担什么角色？"]},
        {"question": "如何保证代码质量？介绍实践过的有效手段。", "type": "GENERAL", "category": "综合能力", "topic_summary": "代码质量保证", "difficulty": "medium", "follow_ups": ["Code Review 关注哪些方面？", "质量和进度冲突时怎么处理？"]},
        {"question": "描述一个技术优化案例，动机、方案和效果。", "type": "GENERAL", "category": "综合能力", "topic_summary": "技术优化案例", "difficulty": "medium", "follow_ups": ["优化前后的关键指标变化？", "最大阻力是什么？"]},
    ]
    if len(questions) < 3:
        needed = question_count - len(questions)
        for fb in _FALLBACK_QUESTIONS[:needed]:
            questions.append({
                "id": f"fallback_{len(questions) + 1}",
                "question": fb["question"],
                "type": fb["type"],
                "category": fb["category"],
                "focus_area": fb["topic_summary"],
                "difficulty": fb["difficulty"],
                "follow_ups": fb.get("follow_ups", []),
            })
        questions = questions[:question_count]

    row = MockInterview(
        user_id=user.id,
        target_role=req.target_role,
        jd_text=jd_text[:5000] if jd_text else "",
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


class FollowUpTurn(BaseModel):
    question: str
    answer: str = ""
    source: str = "dynamic"


class AnswerPayload(BaseModel):
    question_id: str
    answer: str = ""
    follow_ups: list[FollowUpTurn] = []


class FollowUpRequest(BaseModel):
    question_id: str
    answer: str = ""
    follow_ups: list[FollowUpTurn] = []


class SubmitRequest(BaseModel):
    answers: list[AnswerPayload]


def _normalize_answer_payload(item: AnswerPayload | dict) -> dict:
    data = item.model_dump() if isinstance(item, AnswerPayload) else dict(item)
    follow_ups = []
    for turn in data.get("follow_ups", []) or []:
        turn_data = turn.model_dump() if isinstance(turn, FollowUpTurn) else dict(turn)
        question = str(turn_data.get("question", "") or "").strip()
        if not question:
            continue
        follow_ups.append(
            {
                "question": question,
                "answer": str(turn_data.get("answer", "") or "").strip(),
                "source": str(turn_data.get("source", "dynamic") or "dynamic"),
            }
        )
    return {
        "question_id": str(data.get("question_id", "") or "").strip(),
        "answer": str(data.get("answer", "") or "").strip(),
        "follow_ups": follow_ups,
    }


@router.post("/{interview_id}/follow-up")
def generate_follow_up(
    interview_id: int,
    req: FollowUpRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate the next dynamic follow-up question for one interview question."""
    row = (
        db.query(MockInterview)
        .filter(MockInterview.id == interview_id, MockInterview.user_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(404, "面试记录不存在")
    if row.status == "evaluated":
        raise HTTPException(400, "该面试已结束，无法继续追问")

    questions = json.loads(row.questions_json or "[]")
    question = next((q for q in questions if q.get("id") == req.question_id), None)
    if not question:
        raise HTTPException(404, "题目不存在")

    main_answer = (req.answer or "").strip()
    if _is_empty_answer(main_answer):
        raise HTTPException(400, "请先完成当前主回答，再生成追问")

    existing_follow_ups = _normalize_answer_payload(
        {"question_id": req.question_id, "follow_ups": req.follow_ups}
    ).get("follow_ups", [])
    max_rounds = 2
    if len(existing_follow_ups) >= max_rounds:
        return {"done": True, "max_rounds": max_rounds, "round": len(existing_follow_ups)}

    profile_data = _build_enriched_profile(user.id, db)
    profile_summary = _build_profile_summary(profile_data)
    preset_follow_ups = question.get("follow_ups", []) or []
    previous_follow_ups = "\n".join(
        f"- 第 {idx + 1} 轮追问：{item['question']}\n  回答：{item.get('answer', '') or '（未作答）'}"
        for idx, item in enumerate(existing_follow_ups)
    ) or "（暂无）"

    follow_up_text = ""
    should_stop = False
    try:
        from backend.skills import invoke_skill

        result = invoke_skill(
            "mock-interview-followup",
            target_role=row.target_role,
            profile_summary=profile_summary,
            question=question.get("question", ""),
            focus_area=question.get("focus_area", ""),
            main_answer=main_answer,
            previous_follow_ups=previous_follow_ups,
            preset_follow_ups="\n".join(f"- {item}" for item in preset_follow_ups) or "（暂无）",
            follow_up_round=len(existing_follow_ups) + 1,
            max_rounds=max_rounds,
        )
        if isinstance(result, dict):
            follow_up_text = str(result.get("follow_up", "") or "").strip()
            should_stop = bool(result.get("should_stop", False))
    except Exception as exc:
        logger.warning("Dynamic follow-up generation failed: %s", exc)

    if should_stop:
        return {"done": True, "max_rounds": max_rounds, "round": len(existing_follow_ups)}

    # If LLM result contains placeholder pattern, discard
    if follow_up_text and _PLACEHOLDER_RE.search(follow_up_text):
        logger.warning("Placeholder detected in dynamic follow_up, will try preset: %s", follow_up_text[:80])
        follow_up_text = ""

    # Dedup: if LLM generated same question as a previous round, discard
    existing_questions = {item["question"] for item in existing_follow_ups}
    if follow_up_text and follow_up_text in existing_questions:
        logger.warning("Duplicate follow_up detected, will try preset")
        follow_up_text = ""

    # Fallback to preset follow-up if dynamic generation failed/empty
    if (not follow_up_text) and len(preset_follow_ups) > len(existing_follow_ups):
        follow_up_text = str(preset_follow_ups[len(existing_follow_ups)] or "").strip()
        # Preset also needs placeholder check
        if follow_up_text and _PLACEHOLDER_RE.search(follow_up_text):
            logger.warning("Placeholder detected in preset follow_up, discarding: %s", follow_up_text[:80])
            follow_up_text = ""

    if not follow_up_text:
        raise HTTPException(500, "追问生成失败，请稍后重试")

    return {
        "follow_up": follow_up_text,
        "round": len(existing_follow_ups) + 1,
        "max_rounds": max_rounds,
        "done": False,
    }


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

    normalized_answers = [_normalize_answer_payload(item) for item in req.answers]
    row.answers_json = json.dumps(normalized_answers, ensure_ascii=False)
    row.status = "in_progress"
    db.commit()

    # Build Q&A pairs for evaluation
    questions = json.loads(row.questions_json or "[]")
    answer_map = {a["question_id"]: a for a in normalized_answers}

    qa_lines = []
    for q in questions:
        qid = q["id"]
        answer_item = answer_map.get(qid, {"answer": "", "follow_ups": []})
        qa_lines.append(f"【题目 {qid}】({q.get('type', '')}) {q['question']}")
        qa_lines.append(f"【主回答】{answer_item.get('answer') or '（未作答）'}")
        for idx, fu in enumerate(answer_item.get("follow_ups", []) or [], start=1):
            qa_lines.append(f"【追问 {qid}-{idx}】{fu.get('question', '')}")
            qa_lines.append(f"【追问回答 {qid}-{idx}】{fu.get('answer') or '（未作答）'}")
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

    # Force 0 score for empty/敷衍 answers (backend enforcement, LLM can't be trusted)
    evaluation = _force_score_empty_answers(
        evaluation,
        questions,
        {qid: item.get("answer", "") for qid, item in answer_map.items()},
    )

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
