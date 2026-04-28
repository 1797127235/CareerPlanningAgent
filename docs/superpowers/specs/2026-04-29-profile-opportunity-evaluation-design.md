# CareerOS 架构重构：从图谱中心到人岗匹配中心

## 背景与问题

CareerOS 当前的核心业务流强依赖静态岗位图谱（`data/graph.json` + `job_nodes` 表）：

```
上传简历 → Profile → 选择图谱节点 → CareerGoal → Report
                              ↑
                    没有节点就卡死，无法生成报告
```

这带来三个问题：
1. **维护负担重**：45 个节点、每个 38 个字段的 `graph.json` 手工维护不可持续
2. **用户体验差**：用户必须先找到图谱节点才能做职业规划，但实际场景往往是"我有一份 JD，想看看差距"
3. **架构耦合深**：Report、Interview、Growth 等模块全部依赖 `CareerGoal.from_node_id`

## 目标架构

将主轴从 `Graph` 收回到 `Profile + Opportunity + Evaluation`：

```
上传简历 → Profile ─┬→ 粘贴 JD → Opportunity ─→ Evaluation ─→ Report
                    └→ 图谱降级为参考数据（不阻塞主流程）
```

| 实体 | 职责 |
|------|------|
| **Profile** | 用户事实画像（backend2 已成型） |
| **Opportunity** | 用户目标机会（JD 原文 + 解析结果） |
| **Evaluation** | Profile vs Opportunity 的差距评估、建议、快照 |
| **Report** | 基于 Evaluation 快照生成的职业规划报告 |
| **Graph** | 降级为参考数据：推荐方向、岗位模板、技能别名参考 |

## 五阶段迁移计划

### Stage 1: Profile 读取归 v2
**分支**: `feat/migrate-profile-read-to-v2`

**目标**: 前端读取画像走 `/api/v2/profiles/me`，不再依赖 v1 `/api/profiles` 和兼容转换。

** backend2 现状 **:
- `GET /api/v2/profiles/me` ✅ 已注册
- `POST /api/v2/profiles` ✅ 已注册
- `POST /api/v2/profiles/parse-preview` ✅ 已注册

**前端改动点**:
- `useProfileData.ts` → 改调 `fetchMyProfileV2()`
- `types/profile.ts` → 适配 V2 扁平结构
- `ProfilePage.tsx` → 展示逻辑重写（education 从对象变数组，projects 从字符串变对象等）
- 所有引用 `ProfileData` 的组件（至少 6 个文件）需要适配

**V1 vs V2 数据格式差异**:
| 字段 | V1 格式 | V2 格式 |
|------|---------|---------|
| education | 单个对象 `{degree, major, school}` | 数组 `[{degree, major, school, graduation_year, duration}]` |
| skills | `{name, level}[]` level: expert/proficient/... | `{name, level}[]` level: beginner/familiar/intermediate/advanced |
| projects | `string[]` 或 `{name, description, tech_stack[]}[]` | `{name, description, tech_stack[], duration, highlights}[]` |
| internships | 无标准结构 | `{company, role, duration, tech_stack[], highlights}[]` |
| quality | 嵌套对象 `profile.quality.completeness` | 无 |
| graph_position | `profile.graph_position` | 无 |
| career_goals | `profile.career_goals` | 无 |

**工作量提醒**: 这不是简单的 API 调用替换，而是数据模型的全面适配。

**V1 Profile 端点兼容策略**:
Stage 1 只迁移"读取画像"到 v2，以下 v1 端点暂留 v1，后续按需迁移：

| V1 端点 | 功能 | Stage 1 策略 |
|---------|------|-------------|
| `GET /api/profiles` | 读取画像 | ❌ 停用，改走 v2 |
| `PUT /api/profiles` | 更新画像 | 暂留 v1（编辑走 v1） |
| `DELETE /api/profiles` | 重置画像 | 暂留 v1 |
| `POST /api/profiles/reparse` | 重新解析 | 暂留 v1 |
| `PATCH /api/profiles/name` | 修改名称 | 暂留 v1 |
| `POST /api/profiles/projects` | 添加项目 | 暂留 v1 |
| `PATCH /api/profiles/projects/{idx}` | 更新项目 | 暂留 v1 |
| `DELETE /api/profiles/projects/{idx}` | 删除项目 | 暂留 v1 |
| `POST /api/profiles/sjt/*` | SJT 测评 | 暂留 v1（独立功能，不阻塞主线） |

> 原则：Stage 1 只保证"上传简历→解析→预览→保存→读取展示"这个链路完全走 v2。编辑画像、SJT 等次要功能继续走 v1，后续阶段再评估是否迁移。

### Stage 2: Opportunity 最小模块
**分支**: `feat/opportunity-v2`

**目标**: 建立第二个输入源——用户粘贴 JD 生成 Opportunity。

**模型位置**: `backend2/models/opportunity.py`（保持 v2 独立，不混在 backend/models/ 里）。需在 `backend2/db/session.py` 的 `init_db()` 中 import 新模型。

**数据模型**:
```python
# backend2/models/opportunity.py
class Opportunity(Base):
    __tablename__ = "opportunities"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    raw_text: Mapped[str] = mapped_column(Text)  # JD 原文，永久保留
    title: Mapped[str | None] = mapped_column(String(128))
    company: Mapped[str | None] = mapped_column(String(128))
    source_url: Mapped[str | None] = mapped_column(String(512))
    parsed_requirements_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
```

**解析结果 Schema** (`parsed_requirements_json` 的结构约束):
```python
class SkillRequirement(BaseModel):
    name: str
    level: str | None = None  # "required" | "preferred" | "nice_to_have"

class ParsedRequirements(BaseModel):
    title: str | None = None
    company: str | None = None
    skills_required: list[SkillRequirement]
    experience_years: int | None = None
    education: str | None = None
    responsibilities: list[str]
    nice_to_have: list[str]
```

**API**:
- `POST /api/v2/opportunities/parse` — 粘贴 JD，LLM 解析出 requirements
- `GET /api/v2/opportunities` — 当前用户的 Opportunity 列表
- `GET /api/v2/opportunities/{id}` — 详情

**约束**:
- 只支持 JD 文本输入（用户通过搜索获取 JD）
- `raw_text` 必须永久保留，LLM 解析结果只是派生数据
- 复用 backend2 现有的 LLM client 做解析

### Stage 3: Evaluation 模块
**分支**: `feat/evaluation-v2`

**目标**: 替代旧 `JDDiagnosis.diagnose()` 的主业务地位。

**数据模型**:
```python
class Evaluation(Base):
    __tablename__ = "evaluations"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"))
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"))
    
    # 快照：防止源数据变化导致历史评估漂移
    profile_snapshot_json: Mapped[dict] = mapped_column(JSON)
    opportunity_snapshot_json: Mapped[dict] = mapped_column(JSON)
    result_json: Mapped[dict] = mapped_column(JSON)
    
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
```

**API**:
- `POST /api/v2/evaluations`
  - 输入：`profile_id`（或 current profile）+ `opportunity_id`
  - 输出：`match_score`, `matched_skills[]`, `gap_skills[]`, `resume_tips[]`, `action_suggestions[]`

**Prompt 策略**:
- 复用现有 JD 诊断的 prompt 思路
- 但输出强制结构化（Pydantic schema），不再自由文本

**评估结果 Schema** (`result_json` 的结构约束):
```python
class MatchedSkill(BaseModel):
    name: str
    user_level: str  # 用户简历中的技能水平
    required_level: str  # JD 要求的水平

class GapSkill(BaseModel):
    name: str
    estimated_hours: int
    priority: str  # "high" | "medium" | "low"

class ActionSuggestion(BaseModel):
    title: str
    description: str
    estimated_hours: int | None = None

class EvaluationResult(BaseModel):
    match_score: float  # 0-100
    matched_skills: list[MatchedSkill]
    gap_skills: list[GapSkill]
    resume_tips: list[str]
    action_suggestions: list[ActionSuggestion]
```

**关键约束**: 保存时必须存完整快照。以后 profile 或 JD 变了，历史 evaluation 不会漂。

### Stage 4: 报告基于 Evaluation 生成
**分支**: `feat/report-from-evaluation`

**目标**: 报告入口从 `CareerGoal/GraphNode` 改为 `Evaluation`。

**新 API**:
- `POST /api/v2/reports/from-evaluation/{evaluation_id}`

**行为**:
- 报告内容从 `evaluation.result_json` + 模板生成
- 保留旧报告页面但降级：没有 Evaluation 时引导用户先粘贴 JD
- 不再强依赖 `CareerGoal.from_node_id`

**⚠️ 风险提示**: `backend/services/report/pipeline.py` 有 1011 行且深度依赖 `growth_snapshot`、`project_record` 等非图谱数据。Stage 4 是五阶段中风险最高的阶段，实施前需先调研报告 pipeline 对非图谱数据的依赖关系，避免"摆脱了图谱却掉进 growth 数据的重构陷阱"。建议先做一次报告生成链路的无损拆解调研。

### Stage 5: 图谱降级
**分支**: `chore/demote-graph-core`

**目标**: 图谱从主流程阻塞项降级为参考数据。

**动作**:
- 前端主导航调整（具体菜单项）：
  - **首页**: 保留
  - **画像**: 保留（已是主入口）
  - **岗位机会**（新增）: 替代原"岗位图谱"的主入口地位
  - **岗位图谱**（降级）: 从主导航移除，收进"更多"或"探索"二级菜单
  - **成长档案**: 保留
  - **报告**: 入口改为基于 Evaluation
- `/graph`、`setCareerGoal`、`RoleDetailPage` 保留但明确为"参考探索"
- `GraphService` 继续运行，定位改为：
  1. 推荐参考方向
  2. 补充岗位模板
  3. 技能/岗位名参考数据
- 不再承担"没有图谱节点就不能生成报告"的职责

## 数据库 Schema 变更

新增两张表（SQLite）：

```sql
CREATE TABLE opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    raw_text TEXT NOT NULL,
    title VARCHAR(128),
    company VARCHAR(128),
    source_url VARCHAR(512),
    parsed_requirements_json TEXT NOT NULL DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    profile_id INTEGER NOT NULL REFERENCES profiles(id),
    opportunity_id INTEGER NOT NULL REFERENCES opportunities(id),
    profile_snapshot_json TEXT NOT NULL DEFAULT '{}',
    opportunity_snapshot_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 前端改动汇总

| 页面/组件 | Stage | 改动 |
|-----------|-------|------|
| `useProfileData.ts` | 1 | 改调 `fetchMyProfileV2()` |
| `types/profile.ts` | 1 | 适配 V2 扁平结构 |
| `ProfilePage.tsx` | 1 | education 数组、projects 对象等展示逻辑 |
| `ProfileReadonlyView` | 1 | 适配 v2 project 对象格式 |
| 引用 `ProfileData` 的组件 | 1 | 至少 6 个文件需检查 |
| Opportunity 列表页 | 2 | 新建 |
| Opportunity 详情/粘贴页 | 2 | 新建 |
| Evaluation 结果页 | 3 | 新建 |
| Report 生成入口 | 4 | 改为从 Evaluation 进入 |
| 主导航 | 5 | 图谱降权 |

## 风险与回滚策略

| 风险 | 缓解措施 |
|------|----------|
| Stage 1 工作量被低估 | 拆分子 PR：先适配 types，再改组件，最后切调用 |
| v1 功能在迁移期间不可用 | 每阶段独立分支，不合并到 main 直到该阶段完整可用 |
| 旧 JD 诊断数据丢失 | Stage 2 启动时把现有 `JDDiagnosis` 记录迁移为 `Opportunity` |
| 报告质量下降（脱离图谱） | Stage 4 保留旧报告作为 fallback，A/B 验证后再完全切换 |
| 用户习惯改变（不再选图谱节点） | Stage 5 保留图谱页面，只是从主流程降级 |

## 验收标准

阶段性完成后，核心链路应变成：

```
用户上传简历
  → 画像保存（v2）
  → 粘贴 JD
  → 生成 Opportunity
  → 生成 Evaluation（含快照）
  → 生成报告
```

整个流程不再需要用户先去图谱里选一个节点。

## 分支执行顺序

```
feat/migrate-profile-read-to-v2
        ↓
feat/opportunity-v2
        ↓
feat/evaluation-v2
        ↓
feat/report-from-evaluation
        ↓
chore/demote-graph-core
```

不要跳序。Profile 和 Opportunity 是输入源，必须先定住。
