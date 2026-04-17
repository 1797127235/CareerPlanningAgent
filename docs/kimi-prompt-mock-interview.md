# Kimi 实现任务：AI 模拟面试功能

## 概述

实现一个独立的 AI 模拟面试功能。用户选择目标岗位后，AI 生成 5 道个性化面试题，用户逐题作答，最后 AI 给出详细评估。

## 需要新建的文件

### 1. 数据库模型：`backend/db_models.py` 末尾新增

```python
class MockInterview(Base):
    __tablename__ = "mock_interviews"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_role = Column(String(256), nullable=False)
    jd_text = Column(Text, default="")
    questions_json = Column(Text)      # JSON: [{id, type, question, focus_area, difficulty}]
    answers_json = Column(Text)        # JSON: [{question_id, answer}]
    evaluation_json = Column(Text)     # JSON: LLM evaluation result
    status = Column(String(32), default="created")  # created | in_progress | evaluated
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
```

### 2. 后端路由：新建 `backend/routers/interview.py`

```python
"""Mock interview router — generate questions, submit answers, get evaluation."""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import get_db
from backend.db_models import MockInterview, Profile, User

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
```

### 3. 注册路由：修改 `backend/app.py`

在 `from backend.routers import (` 块里加一行：
```python
    interview,
```

在 `app.include_router(...)` 块里加一行：
```python
    app.include_router(interview.router, prefix="/api/interview", tags=["模拟面试"])
```

### 4. 前端页面：新建 `frontend/src/pages/InterviewPage.tsx`

这是一个状态机驱动的单页面，4 个阶段：setup → interviewing → evaluating → results。

**设计要求：**
- 使用项目已有的 glass 卡片风格（`className="glass p-6"`）
- 使用 framer-motion 做入场动画（参考 CoachResultPage.tsx 的 motion.div 用法）
- 使用 lucide-react 图标
- 使用 @tanstack/react-query 的 useMutation 调接口
- 使用 rawFetch from '@/api/client' 发请求
- ease 曲线用 `[0.23, 1, 0.32, 1]`

**阶段 1 - Setup（选择岗位）：**
- 一个 input 输入目标岗位名称（如"前端工程师"）
- 一个 textarea 可选粘贴 JD（不必填）
- "开始模拟面试" 按钮 → 调 POST /api/interview/start
- 下方显示历史面试记录列表（GET /api/interview/history），点击可查看结果

**阶段 2 - Interviewing（逐题作答）：**
- 顶部进度条（1/5, 2/5...）
- 当前题目卡片：显示题目类型标签（技术/行为/场景）、题目文字
- textarea 输入答案
- "下一题" 按钮（最后一题变为"提交全部答案"）
- 可以回退修改之前的题

**阶段 3 - Evaluating（等待评估）：**
- loading 动画
- "AI 面试官正在评估你的回答..."

**阶段 4 - Results（评估结果）：**
- 顶部：总分大字展示 + 一句话总评
- 逐题评分卡片列表：
  - 题目、得分（颜色区分：绿/蓝/黄/红）
  - 亮点（strengths）
  - 改进空间（improvements）
  - 参考回答（suggested_answer），可折叠
- 暴露的技能缺口（skill_gaps）标签
- 改进建议（tips）列表
- "再来一次" 按钮

**颜色映射函数：**
```typescript
function scoreColor(s: number) {
  return s >= 80 ? 'text-emerald-600' : s >= 60 ? 'text-blue-600' : s >= 40 ? 'text-amber-600' : 'text-red-500'
}
```

**题目类型标签颜色：**
```typescript
const typeColors: Record<string, { bg: string; text: string }> = {
  technical: { bg: 'bg-blue-50', text: 'text-blue-600' },
  behavioral: { bg: 'bg-purple-50', text: 'text-purple-600' },
  scenario: { bg: 'bg-amber-50', text: 'text-amber-600' },
}
```

### 5. 注册路由：修改 `frontend/src/App.tsx`

在 import 块加：
```typescript
import InterviewPage from '@/pages/InterviewPage'
```

在 Route 块加：
```tsx
<Route path="/interview" element={<InterviewPage />} />
```

### 6. 首页入口：修改 `frontend/src/pages/HomePage.tsx`

在首页合适位置加一个"模拟面试"入口按钮，点击导航到 `/interview`。用 `MessageSquare` 或 `Mic` 图标。

## 注意事项

1. **Skill 文件已创建好**，在 `backend/skills/mock-interview-gen/SKILL.md` 和 `backend/skills/mock-interview-eval/SKILL.md`，不需要修改
2. **数据库会自动建表**（SQLAlchemy create_all），只需在 db_models.py 中定义模型
3. 所有 API 返回直接 return dict，FastAPI 自动转 JSON
4. 前端所有请求用 `rawFetch` from `@/api/client`，它自动带 auth token
5. 面试题目的 `invoke_skill("mock-interview-gen", ...)` 返回的是 list（因为 skill output=json）
6. 评估的 `invoke_skill("mock-interview-eval", ...)` 返回的是 dict
7. 别忘了在 db_models.py 顶部确认 `func` 已从 sqlalchemy 导入（已有）

## 验证步骤

1. 重启后端 → 表自动创建
2. 访问 /interview → 输入岗位名 → 点开始 → 看到 5 道题
3. 逐题作答 → 提交 → 看到评估结果
4. 刷新页面 → 历史列表能看到这次面试
