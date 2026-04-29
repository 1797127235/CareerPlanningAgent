# JD 诊断 v2 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 backend2 中实现纯净的 JD 诊断能力，不依赖岗位图谱，基于 v2 ProfileData 给出结构化诊断结果。

**Architecture:** 分层架构 — parser（LLM 提取 JD 结构）→ evaluator（Profile vs JD 匹配计算）→ repository（DB 读写）→ service（编排）→ router（HTTP 边界）。每层只依赖下一层。evaluator 无 DB/无 graph/无状态副作用，但允许调用 LLM（非纯函数）。

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic v2, OpenAI 兼容 LLM 客户端（backend2/llm/client.py）

**模块边界（必须遵守）：**
```
backend2/services/jd/
  parser.py      ← 只调用 llm/client.py，返回 JDExtract
  evaluator.py   ← 只接收 ProfileData + JDExtract，无 DB/无 graph/无状态副作用，允许调用 LLM
  repository.py  ← 只操作 JDDiagnosisV2 ORM
  service.py     ← 编排 parser + evaluator + repository + get_my_profile
  prompts.py     ← 纯字符串模板，无业务逻辑
```

`backend2/services/jd/` 目录下任何文件禁止 import：
- `backend.services.graph*` / `backend.routers.graph*`
- `backend.services.jd_service`
- `backend.models.JDDiagnosis`（旧表）
- `CareerGoal`, `Report`, `Coach` 相关模块

---

## 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend2/models/jd_diagnosis.py` | 新建 | JDDiagnosisV2 ORM，外键引用共享 users/profiles/profile_parses |
| `backend2/schemas/jd.py` | 新建 | JDExtract, JDDiagnosisResult, JDDiagnosisResponse, JDDiagnosisListItem |
| `backend2/services/jd/prompts.py` | 新建 | parser + evaluator 的 LLM prompt 模板 |
| `backend2/services/jd/parser.py` | 新建 | jd_text → JDExtract（LLM 调用） |
| `backend2/services/jd/evaluator.py` | 新建 | ProfileData + JDExtract → JDDiagnosisResult（纯计算） |
| `backend2/services/jd/repository.py` | 新建 | jd_diagnoses_v2 表 CRUD |
| `backend2/services/jd/service.py` | 新建 | 编排 diagnose / get_history / get_by_id |
| `backend2/services/jd/__init__.py` | 新建 | 包入口 |
| `backend2/routers/jd.py` | 新建 | 三个 API 端点：POST diagnose, GET history, GET {id} |
| `backend2/app.py` | 修改 | 注册 jd router |
| `backend2/db/session.py` | 修改 | init_db 中导入 JDDiagnosisV2 |

---

### Task 1: ORM 模型 + 表创建

**Files:**
- Create: `backend2/models/jd_diagnosis.py`
- Modify: `backend2/db/session.py`

依赖层：引用共享 `users.id`, `profiles.id`, `profile_parses.id`（backend.models 已定义）。不引用 `backend.models.JDDiagnosis`。

- [ ] **Step 1: 新建 ORM 模型**

```python
"""backend2/models/jd_diagnosis.py — JD 诊断 v2 ORM。"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JDDiagnosisV2(Base):
    __tablename__ = "jd_diagnoses_v2"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("profiles.id"), nullable=False
    )
    profile_parse_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("profile_parses.id"), nullable=True
    )

    jd_text: Mapped[str] = mapped_column(Text, nullable=False)
    jd_title: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    company: Mapped[str] = mapped_column(String(128), nullable=False, default="")

    profile_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    jd_extract_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    result_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    match_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
```

- [ ] **Step 2: session.py 注册模型并修正建表调用**

`backend2/db/session.py` 当前维护自己的 `Base`，但所有 ORM 模型（包括新增 `JDDiagnosisV2`）实际注册在 `backend.db.Base` 上。修改 `init_db()`：

```python
def init_db() -> None:
    """Create all tables if they don't exist (idempotent)."""
    from backend.db import Base as SharedBase
    from backend.models import (  # noqa: F401 - shared ORM models
        User, Report, Profile, ProfileParse, CareerGoal,
        JobNode, JobEdge, JobScore,
        GrowthSnapshot, SkillUpdate, ActionProgress,
        ActionPlanV2, PlanWeekProgress,
        ChatSession, ChatMessage,
        JobApplication, InterviewDebrief,
        JDDiagnosis,
        JobNodeIntro, InterviewQuestionBank,
        UserNotification, CoachResult, MockInterview, GrowthEntry,
        ProjectRecord, ProjectLog, InterviewRecord,
        SjtSession,
    )
    from backend2.models.jd_diagnosis import JDDiagnosisV2  # noqa: F401

    # 所有模型注册在 backend.db.Base 上，用 SharedBase 建表
    SharedBase.metadata.create_all(bind=engine)

    # Migrate: add columns for save-profile pipeline（保持原有 migrations 不变）
    with engine.connect() as conn:
        ...
```

- [ ] **Step 3: 启动验证表创建**

启动 backend2，确认 `jd_diagnoses_v2` 表自动创建：

```bash
cd C:\Users\liu\Desktop\CareerPlanningAgent
python -c "from backend2.db.session import init_db; init_db(); print('OK')"
```

Expected: `OK`（无异常）

- [ ] **Step 4: Commit**

```bash
git add backend2/models/jd_diagnosis.py backend2/db/session.py
git commit -m "feat(backend2): add JDDiagnosisV2 ORM and register in init_db"
```

---

### Task 2: Schema 层

**Files:**
- Create: `backend2/schemas/jd.py`
- Modify: `backend2/schemas/__init__.py`

- [ ] **Step 1: 新建 schema 文件**

```python
"""backend2/schemas/jd.py — JD 诊断 v2 数据契约。"""
from __future__ import annotations

from pydantic import BaseModel, Field


# ── JD 提取层 ───────────────────────────────────────────────────────────

class BasicRequirements(BaseModel):
    """JD 中的基本要求。"""

    education: str = ""        # 学历要求，如"本科及以上"
    experience: str = ""       # 年限要求，如"3年以上"
    location: str = ""         # 地点要求
    language: str = ""         # 语言要求
    certificates: list[str] = Field(default_factory=list)


class JDExtract(BaseModel):
    """从 JD 文本中提取的结构化信息。"""

    title: str = ""
    company: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    basic_requirements: BasicRequirements = Field(default_factory=BasicRequirements)
    seniority_hint: str = ""  # junior / mid / senior 等弱提示


# ── 诊断结果层 ───────────────────────────────────────────────────────────

class GapSkill(BaseModel):
    """技能缺口。"""

    skill: str = ""
    priority: str = "medium"   # high | medium | low
    reason: str = ""           # 为什么判定为缺口
    evidence: str = ""         # JD 中的原文证据
    action_hint: str = ""      # 建议如何补强


class JDDiagnosisResult(BaseModel):
    """诊断结果：Profile vs JD 的匹配分析。"""

    match_score: int = 0  # 0-100
    matched_skills: list[str] = Field(default_factory=list)
    gap_skills: list[GapSkill] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    resume_tips: list[str] = Field(default_factory=list)
    action_suggestions: list[str] = Field(default_factory=list)


# ── API 响应层 ───────────────────────────────────────────────────────────

class JDDiagnosisResponse(BaseModel):
    """单条诊断详情响应。"""

    id: int
    match_score: int
    jd_title: str
    company: str
    jd_extract: JDExtract
    result: JDDiagnosisResult
    created_at: str


class JDDiagnosisListItem(BaseModel):
    """历史列表项。"""

    id: int
    jd_title: str
    company: str
    match_score: int
    created_at: str


# ── 请求层 ───────────────────────────────────────────────────────────────

class JDDiagnoseRequest(BaseModel):
    """请求 JD 诊断。"""

    jd_text: str = Field(..., min_length=10, description="JD 原文")
    jd_title: str = Field(default="", description="岗位名称（用户可选填写）")
```

- [ ] **Step 2: 修改 schemas/__init__.py**

```python
# 追加导出
from backend2.schemas.jd import (
    BasicRequirements,
    JDExtract,
    JDDiagnosisResult,
    JDDiagnosisResponse,
    JDDiagnosisListItem,
    JDDiagnoseRequest,
    GapSkill,
)
```

- [ ] **Step 3: 验证导入**

```bash
python -c "from backend2.schemas.jd import JDExtract, JDDiagnosisResult; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend2/schemas/jd.py backend2/schemas/__init__.py
git commit -m "feat(backend2): add JD diagnosis v2 schemas"
```

---

### Task 3: Prompts 层

**Files:**
- Create: `backend2/services/jd/prompts.py`

纯字符串常量，无业务逻辑，方便后续调优 prompt 时不触碰 parser/evaluator 代码。

- [ ] **Step 1: 新建 prompts.py**

```python
"""backend2/services/jd/prompts.py — LLM prompt 模板。"""
from __future__ import annotations


# ── Parser Prompt ────────────────────────────────────────────────────────

JD_PARSER_SYSTEM = """你是一名专业的招聘 JD 解析助手。
请从用户提供的职位描述（JD）文本中，提取以下结构化信息并以 JSON 格式输出。
只提取文本中明确出现的信息，不要猜测或编造。

输出 JSON 格式：
{
  "title": "岗位名称",
  "company": "公司名（如有）",
  "responsibilities": ["职责1", "职责2", ...],
  "required_skills": ["必需技能1", "必需技能2", ...],
  "preferred_skills": ["加分技能1", "加分技能2", ...],
  "basic_requirements": {
    "education": "学历要求，如'本科及以上'",
    "experience": "年限要求，如'3年以上'",
    "location": "地点要求",
    "language": "语言要求",
    "certificates": ["证书1", "证书2"]
  },
  "seniority_hint": "职级暗示，如 junior/mid/senior"
}

注意：
- 如果某字段在 JD 中未提及，留空字符串或空数组
- skills 使用标准技术名词，去重
- seniority_hint 仅在 JD 明确提到时填写"""


def build_jd_parser_messages(jd_text: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": JD_PARSER_SYSTEM},
        {"role": "user", "content": f"请解析以下 JD 文本：\n\n{jd_text}"},
    ]


# ── Evaluator Prompt ─────────────────────────────────────────────────────

JD_EVALUATOR_SYSTEM = """你是一名资深的求职顾问，擅长分析候选人与职位的匹配度。
请基于用户画像和 JD 提取信息，给出结构化诊断结果。

你需要输出以下 JSON 格式：
{
  "match_score": 75,
  "matched_skills": ["用户已掌握且 JD 要求的技能"],
  "gap_skills": [
    {
      "skill": "缺口技能名称",
      "priority": "high|medium|low",
      "reason": "为什么判定为缺口",
      "evidence": "JD 中相关原文",
      "action_hint": "建议如何补强"
    }
  ],
  "strengths": ["用户相对于该 JD 的优势点"],
  "risks": ["明显的不匹配风险"],
  "resume_tips": ["针对该 JD 的简历优化建议"],
  "action_suggestions": ["短期可执行的补强建议"]
}

评分规则（match_score 0-100）：
- 80-100：高度匹配，技能覆盖率高，经验年限符合
- 60-79：基本匹配，有少量 gap 但可快速补齐
- 40-59：部分匹配，有明显短板需要较长时间补足
- 0-39：匹配度低，核心要求差距大

注意事项：
- 只基于提供的用户画像和 JD 信息做判断
- 不要假设用户有未提及的技能或经验
- gap_skills 按优先级排序，最多 8 条
- strengths / risks / resume_tips / action_suggestions 每项最多 5 条
- 用中文输出"""


def build_jd_evaluator_messages(
    profile_json: str,
    jd_extract_json: str,
    evidence_json: str = "",
) -> list[dict[str, str]]:
    user_content = (
        f"【用户画像】\n{profile_json}\n\n"
        f"【JD 信息】\n{jd_extract_json}\n\n"
    )
    if evidence_json:
        user_content += (
            f"【本地技能匹配证据（基于规则预计算，供你参考）】\n"
            f"{evidence_json}\n\n"
        )
    user_content += "请综合以上信息给出匹配诊断结果。"
    return [
        {"role": "system", "content": JD_EVALUATOR_SYSTEM},
        {"role": "user", "content": user_content},
    ]
```

- [ ] **Step 2: 验证导入**

```bash
python -c "from backend2.services.jd.prompts import build_jd_parser_messages, build_jd_evaluator_messages; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend2/services/jd/prompts.py
git commit -m "feat(backend2): add JD parser and evaluator prompts"
```

---

### Task 4: Sanitizer + Parser 层

**Files:**
- Create: `backend2/services/jd/sanitizer.py`
- Create: `backend2/services/jd/parser.py`

职责：
- sanitizer：清洗用户粘贴的 JD 文本，截断过长内容、移除 prompt injection 尝试
- parser：接收清洗后的 JD 文本，调用 LLM，返回 `JDExtract`

- [ ] **Step 1: 新建 sanitizer.py**

```python
"""backend2/services/jd/sanitizer.py — JD 文本清洗，防御 prompt injection。"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# 常见 prompt injection 模式（大小写不敏感）
_INJECTION_PATTERNS = [
    re.compile(r"```\s*(?:system|instructions?|ignore|override).*?```", re.IGNORECASE | re.DOTALL),
    re.compile(r"ignore\s+(?:all\s+)?(?:previous|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"forget\s+(?:all\s+)?(?:previous|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:a|an)\s+", re.IGNORECASE),
    re.compile(r"disregard\s+(?:the\s+)?(?:previous|above)\s+instructions?", re.IGNORECASE),
]

_MAX_JD_LENGTH = 15000


def sanitize_jd_text(text: str, max_length: int = _MAX_JD_LENGTH) -> str:
    """清洗 JD 文本。

    - 截断过长文本（默认 15KB，约 5000 汉字）
    - 移除常见 prompt injection 标记
    - 保留正常 JD 内容
    """
    if not text:
        return ""

    text = text.strip()

    # 截断
    if len(text) > max_length:
        logger.info("JD 文本过长，截断至 %d 字符", max_length)
        text = text[:max_length]

    # 清洗 injection
    original_len = len(text)
    for pattern in _INJECTION_PATTERNS:
        text = pattern.sub("[BLOCKED]", text)

    if len(text) < original_len:
        logger.warning("JD 文本中发现并移除可疑内容")

    return text.strip()
```

- [ ] **Step 2: 新建 parser.py（调用 sanitizer）**

```python
"""backend2/services/jd/parser.py — JD 文本结构化提取。"""
from __future__ import annotations

import logging

from backend2.llm.client import llm_chat, parse_json_response
from backend2.schemas.jd import JDExtract
from backend2.services.jd.prompts import build_jd_parser_messages
from backend2.services.jd.sanitizer import sanitize_jd_text

logger = logging.getLogger(__name__)


def parse_jd(jd_text: str) -> JDExtract:
    """将 JD 原文解析为结构化 JDExtract。

    流程：
    1. 清洗 JD 文本（防 prompt injection）
    2. 调用 LLM 提取结构化信息
    3. 解析 JSON 响应
    4. 校验并返回 JDExtract

    LLM 调用失败或解析失败时返回空 JDExtract（各字段为默认值）。
    """
    # 1. 清洗
    cleaned = sanitize_jd_text(jd_text)
    if not cleaned or len(cleaned) < 10:
        logger.warning("JD 文本过短或清洗后为空: len=%d", len(cleaned))
        return JDExtract()

    # 2. 调用 LLM
    messages = build_jd_parser_messages(cleaned)
    try:
        raw = llm_chat(messages, temperature=0.3, timeout=60)
    except Exception:
        logger.exception("JD parser LLM 调用失败")
        return JDExtract()

    if not raw:
        logger.warning("JD parser LLM 返回空")
        return JDExtract()

    # 3. 解析 JSON
    try:
        data = parse_json_response(raw)
    except Exception:
        logger.exception("JD parser JSON 解析失败")
        return JDExtract()

    if not data:
        logger.warning("JD parser 无法从 LLM 响应解析 JSON")
        return JDExtract()

    # 4. 校验
    try:
        return JDExtract.model_validate(data)
    except Exception as exc:
        logger.warning("JD parser 校验失败: %s", exc)
        return JDExtract()
```

- [ ] **Step 3: 验证导入**

```bash
python -c "from backend2.services.jd.sanitizer import sanitize_jd_text; from backend2.services.jd.parser import parse_jd; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend2/services/jd/sanitizer.py backend2/services/jd/parser.py
git commit -m "feat(backend2): add JD sanitizer and parser layer"
```

---

### Task 5: Evidence Matcher + Evaluator 层

**Files:**
- Create: `backend2/services/jd/evidence.py`
- Create: `backend2/services/jd/evaluator.py`

**约束**：只接收 `ProfileData` + `JDExtract`，不读数据库、不访问 graph / history / report / coach / application 数据、不修改任何状态。允许调用 LLM。

- [ ] **Step 1: 新建 evidence.py（本地技能匹配证据）**

```python
"""backend2/services/jd/evidence.py — 本地规则匹配证据。

不调用 LLM，不查数据库，纯本地计算：
- 从 ProfileData 提取所有技能（skills + projects.tech_stack）
- 与 JDExtract.required_skills / preferred_skills 做交集和差集
- 结果作为 LLM 的输入证据
"""
from __future__ import annotations

import logging

from backend2.schemas.jd import JDExtract
from backend2.schemas.profile import ProfileData

logger = logging.getLogger(__name__)


def _collect_user_skills(profile: ProfileData) -> set[str]:
    """收集用户画像中所有技能名称（去重、小写）。"""
    skills: set[str] = set()

    for item in profile.skills:
        name = getattr(item, "name", str(item))
        if name:
            skills.add(name.strip().lower())

    for project in profile.projects:
        for tech in getattr(project, "tech_stack", []):
            if tech:
                skills.add(tech.strip().lower())

    return skills


def _match_skill(jd_skill: str, user_skills: set[str]) -> bool:
    """判断 JD 技能是否在用户技能中（子串匹配，大小写不敏感）。"""
    jd_lower = jd_skill.strip().lower()
    if not jd_lower:
        return False
    for us in user_skills:
        if jd_lower in us or us in jd_lower:
            return True
    return False


def build_skill_evidence(profile: ProfileData, jd: JDExtract) -> dict:
    """构建技能匹配证据。

    返回：
    {
        "user_skills": ["python", "go", ...],
        "required_skills": ["Python", "Kubernetes", ...],
        "preferred_skills": ["Redis", "Kafka", ...],
        "matched_required": ["Python"],
        "gap_required": ["Kubernetes"],
        "matched_preferred": ["Redis"],
        "gap_preferred": ["Kafka"],
        "required_coverage": "50%",
        "preferred_coverage": "50%",
    }
    """
    user_skills = _collect_user_skills(profile)

    required = [s.strip() for s in jd.required_skills if s.strip()]
    preferred = [s.strip() for s in jd.preferred_skills if s.strip()]

    matched_required = [s for s in required if _match_skill(s, user_skills)]
    gap_required = [s for s in required if not _match_skill(s, user_skills)]
    matched_preferred = [s for s in preferred if _match_skill(s, user_skills)]
    gap_preferred = [s for s in preferred if not _match_skill(s, user_skills)]

    req_cov = f"{len(matched_required)}/{len(required)} ({len(matched_required)*100//max(len(required),1)}%)"
    pref_cov = f"{len(matched_preferred)}/{len(preferred)} ({len(matched_preferred)*100//max(len(preferred),1)}%)"

    return {
        "user_skills": sorted(user_skills),
        "required_skills": required,
        "preferred_skills": preferred,
        "matched_required": matched_required,
        "gap_required": gap_required,
        "matched_preferred": matched_preferred,
        "gap_preferred": gap_preferred,
        "required_coverage": req_cov,
        "preferred_coverage": pref_cov,
    }
```

- [ ] **Step 2: 新建 evaluator.py（调用 evidence + LLM）**

```python
"""backend2/services/jd/evaluator.py — Profile vs JD 匹配评估。

约束：
- 不读数据库
- 不访问 graph / history / report / coach / application
- 不修改任何状态
- 允许调用 LLM（无状态副作用）
- 先计算本地 evidence，再调用 LLM
- 只接收 ProfileData + JDExtract，返回 JDDiagnosisResult
"""
from __future__ import annotations

import json
import logging

from backend2.llm.client import llm_chat, parse_json_response
from backend2.schemas.jd import JDExtract, JDDiagnosisResult
from backend2.schemas.profile import ProfileData
from backend2.services.jd.evidence import build_skill_evidence
from backend2.services.jd.prompts import build_jd_evaluator_messages

logger = logging.getLogger(__name__)


def evaluate(profile: ProfileData, jd: JDExtract) -> JDDiagnosisResult:
    """评估用户画像与 JD 的匹配度。

    流程：
    1. 本地计算技能匹配证据
    2. 调用 LLM 进行深度匹配分析（evidence 作为输入参考）
    3. 返回结构化诊断结果

    LLM 失败时返回默认空结果（match_score=0）。
    """
    # 1. 本地 evidence
    evidence = build_skill_evidence(profile, jd)
    evidence_json = json.dumps(evidence, ensure_ascii=False, indent=2)

    # 2. 准备 LLM 输入
    profile_json = json.dumps(profile.model_dump(mode="json"), ensure_ascii=False)
    jd_extract_json = json.dumps(jd.model_dump(mode="json"), ensure_ascii=False)

    messages = build_jd_evaluator_messages(profile_json, jd_extract_json, evidence_json)

    # 3. 调用 LLM
    try:
        raw = llm_chat(messages, temperature=0.5, timeout=90)
    except Exception:
        logger.exception("Evaluator LLM 调用失败")
        return JDDiagnosisResult()

    if not raw:
        logger.warning("Evaluator LLM 返回空")
        return JDDiagnosisResult()

    # 4. 解析 JSON
    try:
        data = parse_json_response(raw)
    except Exception:
        logger.exception("Evaluator JSON 解析失败")
        return JDDiagnosisResult()

    if not data:
        logger.warning("Evaluator 无法从 LLM 响应解析 JSON")
        return JDDiagnosisResult()

    # 5. 校验
    try:
        return JDDiagnosisResult.model_validate(data)
    except Exception as exc:
        logger.warning("Evaluator 校验失败: %s", exc)
        return JDDiagnosisResult()
```

- [ ] **Step 3: 验证导入**

```bash
python -c "from backend2.services.jd.evidence import build_skill_evidence; from backend2.services.jd.evaluator import evaluate; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend2/services/jd/evidence.py backend2/services/jd/evaluator.py
git commit -m "feat(backend2): add JD evidence matcher and evaluator layer"
```

---

### Task 6: Repository 层

**Files:**
- Create: `backend2/services/jd/repository.py`

- [ ] **Step 1: 新建 repository.py**

```python
"""backend2/services/jd/repository.py — jd_diagnoses_v2 表 CRUD。"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend2.models.jd_diagnosis import JDDiagnosisV2
from backend2.schemas.jd import JDExtract, JDDiagnosisResult

logger = logging.getLogger(__name__)


def create_diagnosis(
    db: Session,
    *,
    user_id: int,
    profile_id: int,
    profile_parse_id: int | None,
    jd_text: str,
    jd_title: str,
    company: str,
    profile_snapshot: dict,
    jd_extract: JDExtract,
    result: JDDiagnosisResult,
) -> JDDiagnosisV2:
    """创建一条诊断记录。"""
    record = JDDiagnosisV2(
        user_id=user_id,
        profile_id=profile_id,
        profile_parse_id=profile_parse_id,
        jd_text=jd_text,
        jd_title=jd_title or jd_extract.title or "",
        company=company or jd_extract.company or "",
        profile_snapshot_json=json.dumps(profile_snapshot, ensure_ascii=False),
        jd_extract_json=json.dumps(jd_extract.model_dump(mode="json"), ensure_ascii=False),
        result_json=json.dumps(result.model_dump(mode="json"), ensure_ascii=False),
        match_score=result.match_score,
    )
    db.add(record)
    db.flush()
    db.refresh(record)
    logger.info(
        "诊断记录创建: id=%d, user_id=%d, score=%d",
        record.id, user_id, result.match_score,
    )
    return record


def get_history(db: Session, user_id: int, limit: int = 50) -> list[JDDiagnosisV2]:
    """获取用户诊断历史，按 created_at desc。"""
    return (
        db.query(JDDiagnosisV2)
        .filter(JDDiagnosisV2.user_id == user_id)
        .order_by(JDDiagnosisV2.created_at.desc())
        .limit(limit)
        .all()
    )


def get_by_id(db: Session, diagnosis_id: int, user_id: int) -> JDDiagnosisV2 | None:
    """获取单条诊断详情（校验 user_id 权限）。"""
    return (
        db.query(JDDiagnosisV2)
        .filter(JDDiagnosisV2.id == diagnosis_id, JDDiagnosisV2.user_id == user_id)
        .first()
    )
```

- [ ] **Step 2: 验证导入**

```bash
python -c "from backend2.services.jd.repository import create_diagnosis, get_history, get_by_id; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend2/services/jd/repository.py
git commit -m "feat(backend2): add JD diagnosis repository layer"
```

---

### Task 7: Service 编排层

**Files:**
- Create: `backend2/services/jd/service.py`

职责：编排 parser → evaluator → repository，处理业务逻辑（如从 profile 获取 parse_id）。

- [ ] **Step 1: 新建 service.py**

```python
"""backend2/services/jd/service.py — JD 诊断业务编排。"""
from __future__ import annotations

import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend2.schemas.jd import (
    JDExtract,
    JDDiagnosisResponse,
    JDDiagnosisListItem,
    JDDiagnosisResult,
    JDDiagnoseRequest,
)
from backend2.schemas.profile import ProfileData
from backend2.services.jd.evaluator import evaluate
from backend2.services.jd.parser import parse_jd
from backend2.services.jd.repository import create_diagnosis, get_by_id, get_history
from backend2.services.profile.service import get_my_profile

logger = logging.getLogger(__name__)


def _format_dt(dt) -> str:
    """将 datetime 格式化为 ISO 字符串。"""
    if dt is None:
        return ""
    return dt.isoformat()


def _to_response(record) -> JDDiagnosisResponse:
    """将 ORM 记录转换为 API 响应。"""
    import json

    jd_extract = JDExtract.model_validate_json(record.jd_extract_json or "{}")
    result = JDDiagnosisResult.model_validate_json(record.result_json or "{}")

    return JDDiagnosisResponse(
        id=record.id,
        match_score=record.match_score,
        jd_title=record.jd_title,
        company=record.company,
        jd_extract=jd_extract,
        result=result,
        created_at=_format_dt(record.created_at),
    )


def diagnose(
    db: Session,
    user_id: int,
    request: JDDiagnoseRequest,
) -> JDDiagnosisResponse:
    """执行 JD 诊断完整流程。

    1. 读取用户最新画像
    2. 解析 JD 文本
    3. 评估匹配度
    4. 保存诊断快照
    5. 返回响应
    """
    # 1. 读取画像
    profile = get_my_profile(db, user_id)
    profile_id = _resolve_profile_id(db, user_id)
    parse_id = _resolve_parse_id(db, profile_id)

    # 2. 解析 JD
    jd_extract = parse_jd(request.jd_text)
    if request.jd_title:
        jd_extract.title = request.jd_title

    # 3. 评估
    result = evaluate(profile, jd_extract)

    # 4. 保存
    record = create_diagnosis(
        db=db,
        user_id=user_id,
        profile_id=profile_id,
        profile_parse_id=parse_id,
        jd_text=request.jd_text,
        jd_title=request.jd_title,
        company="",
        profile_snapshot=profile.model_dump(mode="json"),
        jd_extract=jd_extract,
        result=result,
    )
    db.commit()

    return _to_response(record)


def get_diagnosis_history(
    db: Session,
    user_id: int,
) -> list[JDDiagnosisListItem]:
    """获取用户诊断历史列表。"""
    records = get_history(db, user_id, limit=50)
    return [
        JDDiagnosisListItem(
            id=r.id,
            jd_title=r.jd_title,
            company=r.company,
            match_score=r.match_score,
            created_at=_format_dt(r.created_at),
        )
        for r in records
    ]


def get_diagnosis_detail(
    db: Session,
    user_id: int,
    diagnosis_id: int,
) -> JDDiagnosisResponse:
    """获取单条诊断详情。"""
    record = get_by_id(db, diagnosis_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="诊断记录不存在")
    return _to_response(record)


# ── 内部辅助 ────────────────────────────────────────────────────────────

def _resolve_profile_id(db: Session, user_id: int) -> int:
    """通过 user_id 获取 profile_id。"""
    from backend.models import Profile

    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="用户未创建画像")
    return profile.id


def _resolve_parse_id(db: Session, profile_id: int) -> int | None:
    """通过 profile_id 获取当前 active_parse_id。"""
    from backend.models import Profile

    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    return profile.active_parse_id if profile else None
```

- [ ] **Step 2: 验证导入**

```bash
python -c "from backend2.services.jd.service import diagnose, get_diagnosis_history, get_diagnosis_detail; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend2/services/jd/service.py
git commit -m "feat(backend2): add JD diagnosis service orchestration"
```

---

### Task 8: Router + App 注册

**Files:**
- Create: `backend2/routers/jd.py`
- Modify: `backend2/app.py`

- [ ] **Step 1: 新建 jd router**

```python
"""backend2/routers/jd.py — JD 诊断 v2 API 路由。"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.models import User
from backend2.core.security import get_current_user
from backend2.db.session import get_db
from backend2.schemas.jd import (
    JDDiagnoseRequest,
    JDDiagnosisListItem,
    JDDiagnosisResponse,
)
from backend2.services.jd.service import (
    diagnose,
    get_diagnosis_detail,
    get_diagnosis_history,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jd", tags=["jd-diagnosis"])


@router.post("/diagnose", response_model=JDDiagnosisResponse)
def post_diagnose(
    request: JDDiagnoseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JDDiagnosisResponse:
    """请求 JD 诊断。

    基于当前用户最新画像，对粘贴的 JD 文本进行匹配分析。
    """
    try:
        return diagnose(db=db, user_id=current_user.id, request=request)
    except HTTPException:
        raise
    except Exception:
        logger.exception("JD 诊断失败: user_id=%d", current_user.id)
        raise HTTPException(status_code=500, detail="诊断失败，请稍后重试")


@router.get("/history", response_model=list[JDDiagnosisListItem])
def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[JDDiagnosisListItem]:
    """获取当前用户的 JD 诊断历史列表。"""
    try:
        return get_diagnosis_history(db=db, user_id=current_user.id)
    except Exception:
        logger.exception("获取诊断历史失败: user_id=%d", current_user.id)
        raise HTTPException(status_code=500, detail="获取历史失败")


@router.get("/{diagnosis_id}", response_model=JDDiagnosisResponse)
def get_detail(
    diagnosis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JDDiagnosisResponse:
    """获取单条诊断详情。"""
    try:
        return get_diagnosis_detail(
            db=db, user_id=current_user.id, diagnosis_id=diagnosis_id
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("获取诊断详情失败: user_id=%d, id=%d", current_user.id, diagnosis_id)
        raise HTTPException(status_code=500, detail="获取详情失败")
```

- [ ] **Step 2: 修改 app.py 注册 router**

在 `backend2/app.py` 的 router 注册区域添加：

```python
from backend2.routers import health, profiles, jd
app.include_router(jd.router, prefix="/api/v2", tags=["jd-diagnosis"])
```

（保持与现有 profiles router 注册方式一致）

- [ ] **Step 3: 创建 `backend2/services/jd/__init__.py`**

```python
"""backend2/services/jd — JD 诊断 v2 服务包。"""
```

- [ ] **Step 4: 验证启动**

```bash
python -c "from backend2.app import create_app; app = create_app(); print('OK, routes:', [r.path for r in app.routes if hasattr(r, 'path') and '/jd' in r.path])"
```

Expected: 包含 `/api/v2/jd/diagnose`, `/api/v2/jd/history`, `/api/v2/jd/{diagnosis_id}`

- [ ] **Step 5: Commit**

```bash
git add backend2/routers/jd.py backend2/app.py backend2/services/jd/__init__.py
git commit -m "feat(backend2): add JD diagnosis v2 router and register in app"
```

---

### Task 9: 端到端验收测试

**Files:**
- 无新建文件，使用已有环境验证

验收标准（来自 spec）：
- [ ] 用户粘贴 JD 文本，系统基于当前 v2 画像给出诊断
- [ ] 诊断结果包含：match_score、matched_skills、gap_skills、resume_tips
- [ ] 诊断结果保存到 `jd_diagnoses_v2` 表，含 `profile_snapshot_json`
- [ ] 支持查看历史诊断列表
- [ ] 支持查看单条诊断详情
- [ ] 全程不依赖岗位图谱
- [ ] backend2 不写入旧 `JDDiagnosis` 表
- [ ] 使用 2-3 份真实 JD 样本跑通 diagnose / history / detail

**测试步骤：**

- [ ] **Step 1: 启动 backend2**

```bash
cd C:\Users\liu\Desktop\CareerPlanningAgent
python -m uvicorn backend2.app:app --port 8001 --reload
```

- [ ] **Step 2: 确保已有用户和画像**

如果没有：
1. 注册/登录用户获取 token
2. 上传简历并保存画像（通过 `/api/v2/profiles/parse-preview` + `/api/v2/profiles`）

- [ ] **Step 3: 测试 POST /api/v2/jd/diagnose**

使用 curl / Postman / 前端页面：

```bash
# 替换 $TOKEN 为实际 JWT token
curl -X POST http://127.0.0.1:8001/api/v2/jd/diagnose \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jd_text": "字节跳动 后端开发工程师\n\n职位描述：\n1. 负责字节跳动核心产品的后端架构设计与开发\n2. 使用 Go/Java 进行高并发系统开发\n3. 参与分布式系统设计与优化\n\n职位要求：\n1. 本科及以上学历，计算机相关专业\n2. 3年以上后端开发经验\n3. 精通 Go 或 Java，熟悉常用框架\n4. 熟悉 MySQL、Redis、消息队列\n5. 熟悉微服务架构，有 Kubernetes 经验优先\n6. 良好的沟通能力和团队协作精神",
    "jd_title": "后端开发工程师"
  }'
```

Expected: 返回 `JDDiagnosisResponse`，包含 `match_score`, `result.matched_skills`, `result.gap_skills`, `result.resume_tips`

- [ ] **Step 4: 验证数据库写入**

```bash
sqlite3 data/app_state/app.db "SELECT id, match_score, jd_title, profile_snapshot_json FROM jd_diagnoses_v2 ORDER BY id DESC LIMIT 1;"
```

Expected: 有记录，且 `profile_snapshot_json` 不为空

- [ ] **Step 5: 测试 GET /api/v2/jd/history**

```bash
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8001/api/v2/jd/history
```

Expected: 返回列表，包含刚才创建的诊断记录

- [ ] **Step 6: 测试 GET /api/v2/jd/{id}**

```bash
# 替换 $ID 为 Step 3 返回的 id
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8001/api/v2/jd/$ID
```

Expected: 返回完整 `JDDiagnosisResponse`

- [ ] **Step 7: 用 2-3 份不同 JD 重复测试**

至少覆盖：
- 技术岗 JD（如上）
- 产品岗 JD（要求不同技能栈）
- 应届生/实习 JD（年限要求低）

- [ ] **Step 8: 验证无 graph 依赖**

```bash
python -c "
import ast, sys

FILES = [
    'backend2/services/jd/parser.py',
    'backend2/services/jd/evaluator.py',
    'backend2/services/jd/service.py',
    'backend2/services/jd/repository.py',
    'backend2/routers/jd.py',
]

# 精确禁止的旧模块路径和类名
BANNED = {
    'backend.services.graph',
    'backend.routers.graph',
    'backend.services.jd_service',
    'backend.models.JDDiagnosis',  # 旧表，不是 JDDiagnosisV2
    'CareerGoal',
    'Report',
    'CoachResult',
    'Coach',
}

for f in FILES:
    with open(f) as fh:
        tree = ast.parse(fh.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                full = alias.name
                if any(b in full for b in BANNED):
                    print(f'BAD import in {f}: {full}')
                    sys.exit(1)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ''
            for alias in node.names:
                full = f'{mod}.{alias.name}' if mod else alias.name
                if any(b in full for b in BANNED):
                    print(f'BAD import in {f}: {full}')
                    sys.exit(1)

print('OK: no banned imports in jd modules')
"
```

Expected: `OK: no banned imports in jd modules`

- [ ] **Step 9: Commit 验收记录**

```bash
git commit --allow-empty -m "test(backend2): JD diagnosis v2 e2e verified"
```

---

## 实施顺序与依赖

```
Task 1 (ORM) ──► Task 2 (Schema) ──► Task 3 (Prompts)
                                            │
Task 4 (Parser) ◄────────────────────────────┘
       │
Task 5 (Evaluator)
       │
Task 6 (Repository)
       │
Task 7 (Service) ──► Task 8 (Router) ──► Task 9 (E2E)
```

每完成一个 Task 后立即 commit，不累积多个 Task 再提交。

---

## 回滚策略

- 仅新增文件 + `backend2/db/session.py` 和 `backend2/app.py` 的两行修改
- 旧 `JDDiagnosis` 表和模型完全不触碰
- 如需回滚：删除新增文件，撤销 session.py 和 app.py 的两行 import/注册即可
