# Kimi 任务：模拟面试接入成长档案

## 目标

模拟面试评估完成后，自动在成长档案中创建一条面试记录（`InterviewRecord`）。这样：
1. 成长档案时间线里能看到模拟面试记录
2. 首页活动热力图自动统计（已有逻辑会查 `InterviewRecord`）
3. 连续天数 streak 自动计入

---

## 改动文件

只改一个文件：`backend/routers/interview.py`

---

## 具体改动

在 `submit_answers` 函数中，评估完成、保存 `evaluation_json` 之后，创建一条 `InterviewRecord`。

### 1. 添加 import

在文件顶部的 import 区域，把 `MockInterview` 那行改为：

```python
from backend.db_models import MockInterview, InterviewRecord, Profile, User
```

### 2. 在 `submit_answers` 函数末尾添加

在 `row.status = "evaluated"` 和 `db.commit()` 之间（或 `db.commit()` 之后），添加创建 `InterviewRecord` 的代码：

找到这段代码：
```python
    row.evaluation_json = json.dumps(evaluation, ensure_ascii=False)
    row.status = "evaluated"
    db.commit()

    return evaluation
```

改为：
```python
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
        reflection=summary,
        ai_analysis=json.dumps(ai_analysis_data, ensure_ascii=False),
    )
    db.add(interview_record)
    db.commit()

    return evaluation
```

---

## 字段映射说明

| InterviewRecord 字段 | 填什么 | 说明 |
|---|---|---|
| `company` | `"AI 模拟"` | 区分真实面试和模拟面试 |
| `position` | `row.target_role` | 用户填的目标岗位 |
| `round` | `"模拟面试"` | 标识这是模拟面试 |
| `content_summary` | 题目类型+方向+得分 | 一句话概括，在成长档案时间线显示 |
| `self_rating` | 根据分数自动计算 | ≥80 good, ≥60 medium, <60 bad |
| `result` | 根据分数判断 | ≥60 passed, <60 failed |
| `reflection` | evaluation.summary | AI 的一句话总评 |
| `ai_analysis` | 完整评估 JSON | 包含 mock_interview_id 方便回溯 |

---

## 不改的部分

- `InterviewRecord` 模型 — 不动，现有字段完全够用
- 成长档案前端 `GrowthLogV2Page.tsx` — 不动，已有逻辑会自动展示 InterviewRecord
- 活动热力图 `dashboard_service.py` — 不动，已有逻辑会自动统计 InterviewRecord
- 前端 `InterviewPage.tsx` — 不动

---

## 验证

1. 完成一次模拟面试，提交答案
2. 打开成长档案页面，应该能看到一条面试记录，显示"AI 模拟 · 目标岗位 · 模拟面试"
3. 首页活动热力图当天应该多一个活动计数
4. 数据库 `interview_records` 表应该新增一行，`company="AI 模拟"`，`ai_analysis` 包含 `"source": "mock_interview"`
