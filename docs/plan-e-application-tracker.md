# Plan E — 求职跟踪 + 面试复盘模块技术方案

## 背景与问题

系统当前的用户旅程在 JD 诊断完成后即断链——用户投递简历、参加面试、面试复盘等关键行动完全发生在系统感知范围之外，导致：

1. **无回访动机**：面试完成后系统没有出现，用户不会主动回来复盘
2. **成长断链**：面试经验无法沉淀进画像，下次诊断仍是旧数据
3. **留存极差**：核心价值主张「陪伴成长」无法兑现

本模块目标是在现有系统上建立完整的**投递跟踪 → 面试提醒 → 复盘闭环**。

---

## 用户旅程（目标态）

```
JD 诊断完成
    │  点击「我要投这个岗位」
    ▼
创建投递记录（绑定 JD 诊断）
    │  填写公司/岗位 + 投递日期
    ▼
手动推进状态：已投递 → 获得面试
    │  设置面试时间
    ▼
系统提醒（面试前 24h）
    │  首页 banner → P1 邮件
    ▼
面试完成 → 用户手动标记
    │  首页出现复盘引导入口
    ▼
录入面试题目 + 我的回答
    │  → P2 支持上传录音文件
    ▼
LLM 生成复盘报告（不足 + 改进建议）
    │
    ▼
复盘结果 → 更新画像薄弱技能（P3）
```

---

## 数据模型

### JobApplication 表

```python
class JobApplication(Base):
    __tablename__ = "job_applications"

    id              = Column(Integer, primary_key=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    jd_diagnosis_id = Column(Integer, ForeignKey("jd_diagnoses.id"), nullable=True)

    # 岗位信息（可选填充，也可从关联诊断中读取）
    company         = Column(String(256), nullable=True)
    position        = Column(String(256), nullable=True)
    job_url         = Column(String(512), nullable=True)

    # 状态机
    status          = Column(String(32), default="pending", nullable=False)
    # pending | applied | screening | scheduled | interviewed | debriefed | offer | rejected | withdrawn

    # 时间节点
    applied_at      = Column(DateTime, nullable=True)
    interview_at    = Column(DateTime, nullable=True)   # 面试预定时间（用于提醒）
    completed_at    = Column(DateTime, nullable=True)   # 实际完成时间

    # 关联复盘
    debrief_id      = Column(Integer, ForeignKey("interview_debriefs.id"), nullable=True)

    notes           = Column(Text, nullable=True)       # 用户备注
    reminder_sent   = Column(Boolean, default=False)    # 提醒是否已发送

    created_at      = Column(DateTime, default=func.now())
    updated_at      = Column(DateTime, default=func.now(), onupdate=func.now())
```

### InterviewDebrief 表

```python
class InterviewDebrief(Base):
    __tablename__ = "interview_debriefs"

    id              = Column(Integer, primary_key=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    application_id  = Column(Integer, ForeignKey("job_applications.id"), nullable=True)

    # 输入内容
    input_mode      = Column(String(16), default="text")  # text | audio（P2）
    raw_input       = Column(Text, nullable=True)         # 用户原始输入（JSON 字符串）
    # 结构：[{"question": "...", "answer": "..."}, ...]

    # P2：录音相关
    audio_file_path = Column(String(512), nullable=True)  # 上传文件路径
    transcript      = Column(Text, nullable=True)         # ASR 转录结果

    # 输出内容
    report_json     = Column(Text, nullable=True)         # LLM 复盘报告（JSON）
    # 结构见下方「复盘报告格式」

    created_at      = Column(DateTime, default=func.now())
```

### 复盘报告 JSON 结构

```json
{
  "overall_score": 72,
  "summary": "一句话总结整体表现",
  "question_reviews": [
    {
      "question": "面试官提问原文",
      "your_answer": "你的回答原文",
      "score": 65,
      "strengths": ["亮点1", "亮点2"],
      "weaknesses": ["不足1", "不足2"],
      "suggested_answer": "参考回答思路",
      "skill_tags": ["系统设计", "沟通表达"]
    }
  ],
  "gap_skills": [
    { "skill": "系统设计", "priority": "high", "advice": "建议..." }
  ],
  "overall_tips": ["改进建议1", "改进建议2"]
}
```

---

## 后端实现

### API 路由（`backend/routers/applications.py`）

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/applications` | 创建投递记录 |
| GET | `/api/applications` | 获取当前用户所有投递记录 |
| GET | `/api/applications/{id}` | 获取单条记录详情 |
| PATCH | `/api/applications/{id}/status` | 更新状态 |
| PATCH | `/api/applications/{id}/interview-time` | 设置面试时间 |
| DELETE | `/api/applications/{id}` | 删除记录 |
| POST | `/api/applications/{id}/debrief` | 提交复盘（文字模式） |
| GET | `/api/applications/{id}/debrief` | 获取复盘报告 |

### 面试提醒服务（`backend/services/reminder_service.py`）

使用 APScheduler 每小时轮询一次：

```python
from apscheduler.schedulers.background import BackgroundScheduler

def check_interview_reminders(db: Session):
    """查找面试时间在 24h 内且未发送提醒的记录，写入 guidance 提醒标记"""
    now = datetime.utcnow()
    upcoming = (
        db.query(JobApplication)
        .filter(
            JobApplication.status == "scheduled",
            JobApplication.reminder_sent == False,
            JobApplication.interview_at.between(now, now + timedelta(hours=24)),
        )
        .all()
    )
    for app in upcoming:
        app.reminder_sent = True
        # P1: 这里插入邮件发送逻辑
    db.commit()

scheduler = BackgroundScheduler()
scheduler.add_job(check_interview_reminders, "interval", hours=1)
```

**提醒展示**：在现有 `guidance` API（`/api/guidance?stage=home`）中增加一条规则——
检查用户是否有 `reminder_sent=True` 且 `status=scheduled` 的记录，有则在首页返回面试提醒 banner。

### 复盘 LLM Prompt（`backend/services/debrief_service.py`）

```
你是一位专业的面试复盘教练。请根据以下信息对这次面试进行深度复盘。

## 岗位信息
{jd_text}

## 候选人技能画像
{profile_skills}

## 面试题目与回答
{qa_list}

## 评分与复盘要求
- 对每道题目：给出 0-100 分，列出亮点、不足、参考回答思路
- 综合评分：加权平均
- 识别核心短板技能，给出优先级和改进路径
- 语气：直接、具体、有建设性，禁止空洞表扬

输出严格 JSON，格式见 schema。
```

---

## 前端实现

### 新增路由
`/applications` — 求职跟踪页（新页面 `ApplicationsPage.tsx`）

### 组件结构

```
ApplicationsPage
├── ApplicationBoard         # 看板视图（按状态分列）
│   ├── ApplicationCard      # 单条投递卡片
│   └── AddApplicationBtn    # 从 JD 诊断导入 or 手动新建
├── ApplicationDetail        # 侧边抽屉/详情页
│   ├── StatusStepper        # 状态步进器
│   ├── InterviewTimePicker  # 面试时间设置
│   └── DebriefEntryBtn      # 进入复盘入口
└── DebriefPage              # 复盘页
    ├── QAInputList          # 题目+回答录入列表
    ├── DebriefReport        # 复盘报告展示
    └── (P2) AudioUploader   # 录音上传
```

### JD 诊断页接入点

在 `MatchResult.tsx` 的 Action Buttons 区域，将「开启专属模拟面试」旁边新增：

```tsx
<button onClick={() => navigate('/applications/new?from_jd=' + result.id)}>
  记录投递 · 跟踪进度
</button>
```

---

## P2 升级：录音复盘

### 技术路径

```
用户上传录音文件（mp3/m4a/wav）
    │  FastAPI UploadFile → 存储本地 / OSS
    ▼
DashScope 语音识别 API（paraformer-realtime）
    │  开启 diarization（说话人分离）
    ▼
转录结果：[{"speaker": "A", "text": "...", "time": 0.0}, ...]
    │
    ▼
展示给用户确认/编辑（半自动，非全自动）
    │  用户可以修正错误识别、标记哪段是问题哪段是回答
    ▼
结构化后走与文字模式相同的 LLM 复盘流程
```

### 关键风险

| 风险 | 应对措施 |
|------|---------|
| 录音质量差导致识别率低 | 提供手动编辑转录结果的界面，不强依赖 ASR 准确率 |
| 说话人分离效果差 | 用户可手动拖拽段落归属，而非全自动 |
| 文件过大上传慢 | 限制文件大小 50MB，前端压缩后上传 |
| 隐私顾虑 | 转录完成后提示用户可删除原始录音，仅保留文字 |

---

## P3 升级：复盘结果回写画像

复盘完成后，将 `gap_skills` 中 `priority=high` 的技能自动追加到用户画像的 `weak_skills` 字段，下次 JD 诊断时优先对比。

---

## 实施节奏

| 阶段 | 内容 | 估时 |
|------|------|------|
| **P0** | JobApplication 表、状态 CRUD、面试时间 + APScheduler banner 提醒、文字复盘 + LLM 报告 | 1 周 |
| **P1** | 邮件提醒（smtplib）、ApplicationBoard 看板 UI 优化 | 3 天 |
| **P2** | 录音上传 + ASR 转录 + 半自动结构化 + 确认界面 | 1.5 周 |
| **P3** | 复盘结果回写画像薄弱技能 | 2 天 |

---

## 不做的事（边界）

- **不做推送通知**（Web Push）：成本高，P1 邮件已够用
- **不做全自动录音解析**：半自动确认比全自动更可靠，也降低错误风险
- **不做第三方招聘平台同步**：投递状态由用户手动维护，避免爬虫/OAuth 复杂度
- **不做 AI 模拟面试官**：复盘是对已发生面试的分析，与模拟面试（`/practice`）职责分离
