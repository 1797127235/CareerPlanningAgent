# JD 诊断 v2 设计文档

> **目标**：在 backend2 中实现纯净的 JD 诊断能力，不依赖岗位图谱，基于 v2 ProfileData 给出结构化诊断结果。

---

## 1. 背景与约束

### 1.1 现状
- 旧 `backend/routers/jd.py` 和 `backend/services/jd_service.py` 依赖岗位图谱（`graph_service`、`match_to_graph_node`、`find_escape_routes`）
- 岗位图谱是手工维护的确定性数据，难以维护
- 旧 `JDDiagnosis` 表和模型在 `backend/models` 中，backend2 不应写入旧表

### 1.2 约束
- backend2 保持纯净，不依赖岗位图谱
- 不动旧 `JDDiagnosis` 表和模型
- 不主动调用 Report/Coach/CareerGoal/Application Tracking 等模块
- 诊断基于 v2 `ProfileData` 格式

---

## 2. 目标

实现一个能跑的业务闭环：

```
v2 ProfileData + 用户粘贴 JD 文本 -> JD 诊断结果 -> 保存诊断快照
```

### 2.1 第一版范围
- 支持用户粘贴 JD 文本
- 基于当前用户最新画像（v2 `ProfileData`）做匹配诊断
- 输出结构化诊断结果
- 保存诊断历史
- **不依赖**：Graph、Report、Coach、CareerGoal、Application Tracking、Recommendation

---

## 3. 数据模型

### 3.1 ORM 模型（backend2 自建）

```python
# backend2/models/jd_diagnosis.py

class JDDiagnosisV2(Base):
    __tablename__ = "jd_diagnoses_v2"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    profile_id: Mapped[int] = mapped_column(Integer, ForeignKey("profiles.id"), nullable=False)
    profile_parse_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("profile_parses.id"), nullable=True
    )  # 可选：基于哪次简历解析快照

    jd_text: Mapped[str] = mapped_column(Text, nullable=False)
    jd_title: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    company: Mapped[str] = mapped_column(String(128), nullable=False, default="")

    profile_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    """诊断当时使用的最终画像快照（confirmed_profile），不因后续编辑而变。"""

    jd_extract_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    result_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    match_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
```

### 3.2 外键边界说明

`JDDiagnosisV2` 是 backend2 自建的 ORM 模型，但外键引用的是现有共享表：
- `users.id`、`profiles.id`、`profile_parses.id` 目前由 `backend.models` 定义
- backend2 **只新增自己的 `jd_diagnoses_v2` 表**，不把旧 `JDDiagnosis` 带进来
- 等旧 backend 退役时，User/Profile 模型再整体迁入 backend2

### 3.3 字段说明

| 字段 | 说明 |
|------|------|
| `jd_text` | JD 原文，永远保留 |
| `jd_extract_json` | JD 结构化提取结果（JDExtract） |
| `result_json` | Profile vs JD 的诊断结果（JDDiagnosisResult） |
| `profile_snapshot_json` | **诊断当时使用的最终画像快照**，不因后续编辑而变 |
| `profile_parse_id` | 可选，记录基于哪次简历解析快照，支持追溯 |
| `match_score` | 综合匹配度，方便列表页排序 |

### 3.3 Schema（Pydantic）

```python
# backend2/schemas/jd.py

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


class JDDiagnosisResponse(BaseModel):
    """API 响应。"""
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
```

---

## 4. API 设计

### 4.1 POST /api/v2/jd/diagnose

请求 JD 诊断。

**Request:**
```json
{
  "jd_text": "字节跳动后端开发工程师...",
  "jd_title": "后端开发工程师"
}
```

**Response:** `JDDiagnosisResponse`

**流程:**
1. 读取当前用户最新 v2 ProfileData
2. Parser：LLM 解析 JD 文本 -> `JDExtract`
3. Evaluator：`ProfileData` + `JDExtract` -> `JDDiagnosisResult`
4. Repository：保存到 `jd_diagnoses_v2`
5. 返回 `JDDiagnosisResponse`

### 4.2 GET /api/v2/jd/history

获取当前用户的诊断历史列表。

**Response:** `list[JDDiagnosisListItem]`，按 `created_at` desc，最多 50 条。

### 4.3 GET /api/v2/jd/{diagnosis_id}

获取单条诊断详情。

**Response:** `JDDiagnosisResponse`

---

## 5. 模块结构

```
backend2/
  models/
    jd_diagnosis.py          # JDDiagnosisV2 ORM

  schemas/
    jd.py                    # JDExtract, JDDiagnosisResult, JDDiagnosisResponse

  routers/
    jd.py                    # 三个 API 端点

  services/
    jd/
      __init__.py
      service.py             # 编排：diagnose() / get_history() / get_by_id()
      parser.py              # jd_text -> JDExtract（LLM prompt）
      evaluator.py           # ProfileData + JDExtract -> JDDiagnosisResult
      repository.py          # JDDiagnosesV2 CRUD
      prompts.py             # LLM prompts
```

### 5.1 职责划分

| 模块 | 职责 |
|------|------|
| `parser.py` | 接收 JD 文本，LLM 提取结构化信息（`JDExtract`） |
| `evaluator.py` | 接收 `ProfileData` + `JDExtract`，计算匹配度、找 gap、给建议。<br>**约束**：只能基于这两个输入，不能查 graph / history / report / application，不能写任何副作用。 |
| `repository.py` | `jd_diagnoses_v2` 表的读写 |
| `service.py` | 编排上述模块，处理业务逻辑 |
| `prompts.py` | 集中管理 LLM prompts |

---

## 6. 与其他模块的关系

### 6.1 依赖
- **Profile 模块**：`backend2/services/profile/service.py` 的 `get_my_profile()` 或直接从 DB 读取
- **User 认证**：`backend2/core/security.py` 的 `get_current_user`

### 6.2 不依赖
- Graph（岗位图谱）
- Report（报告生成）
- Coach（教练洞察）
- CareerGoal（职业目标）
- Application Tracking（投递追踪）
- Recommendation（岗位推荐）

### 6.3 为未来模块提供输入
JD 诊断 v2 的输出可以被后续模块消费：
- Report：基于 `JDDiagnosisResult` 生成报告
- Coach：读取诊断结果给建议
- Application Tracking：关联 `diagnosis_id`
- Graph：作为可选参考（不主动调用）

**关键原则：现在只产出诊断结果，不主动调用它们。**

---

## 7. Prompt 设计

### 7.1 Parser Prompt（JD 文本 -> JDExtract）

从 JD 文本中提取结构化信息：
- 岗位名称、公司名
- 职责描述
- 必需技能、加分技能
- 基本要求（学历、年限等）
- 职级暗示

### 7.2 Evaluator Prompt（ProfileData + JDExtract -> JDDiagnosisResult）

**输入约束**：Evaluator 只能接收 `ProfileData` + `JDExtract`，不能访问：
- 岗位图谱（graph）
- 历史诊断记录
- Report / Coach / CareerGoal / Application Tracking 数据

**输出范围**：
- 基础要求匹配（学历、年限）
- 技能匹配（必需/加分技能的覆盖率）
- 优势识别（用户画像中的亮点与 JD 的契合点）
- 风险提示（明显 gap）
- 简历优化建议
- 行动建议

**不输出：** `graph_context`、`escape_routes`、`coach_insight`

**副作用约束**：Evaluator 是纯粹的计算函数，不产生 DB 写入、不调用外部 API、不修改任何状态。

---

## 8. 迁移策略

### 8.1 不直接搬旧代码
旧 `backend/routers/jd.py` 和 `backend/services/jd_service.py` 不直接搬。

### 8.2 可借鉴的
- 前端页面流程（粘贴 JD -> 展示结果）
- 旧 prompt 中的评分维度思路
- 历史列表字段

### 8.3 不带的
- `graph_context`
- `escape_routes`
- `coach_insight`
- 投递追踪逻辑
- CareerGoal 关联

---

## 9. 验收标准

- [ ] 用户粘贴 JD 文本，系统基于当前 v2 画像给出诊断
- [ ] 诊断结果包含：match_score、matched_skills、gap_skills、resume_tips
- [ ] 诊断结果保存到 `jd_diagnoses_v2` 表，含 `profile_snapshot_json`
- [ ] 支持查看历史诊断列表
- [ ] 支持查看单条诊断详情
- [ ] 全程不依赖岗位图谱
- [ ] backend2 不写入旧 `JDDiagnosis` 表
- [ ] 使用 2-3 份真实 JD 样本跑通 diagnose / history / detail
- [ ] `backend2/services/jd/` 不 import `backend.services.graph` / `backend.routers.graph` / `CareerGoal`

---

## 10. 与数据层重建的关系

这一步是数据层重建的第一块砖：

```
ProfileSnapshot  ->  已有（v2 ProfileData）
JDExtract        ->  本阶段新建
DiagnosisResult  ->  本阶段新建
```

跑通后，后续自然抽象：
- `Opportunity` = `jd_text` + `JDExtract`
- `Evaluation` = `profile_snapshot` + `opportunity_snapshot` + `DiagnosisResult`

**但现在不要把名字做大。**
