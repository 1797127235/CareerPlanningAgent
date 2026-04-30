# 画像闭环重构 Spec

> **目标**：把 Profile 页面从"推荐入口"改成"个人画像管理页"。

---

## 边界（明确不做）

- 不做 LLM 职业推荐
- 不做规则职业推荐
- 不做"推荐岗位 / 推荐方向"
- 不做自动学习路径
- 不做"AI 判断你适合什么"这类话术

> 产品措辞统一为"基于简历和用户补充信息整理出的能力画像"，保持诚实、可解释。

---

## 1. 数据层

### 1.1 扩展 `ProfileData`

在 `backend2/schemas/profile.py` 的 `ProfileData` 中新增以下字段：

```python
class DimensionScore(BaseModel):
    """单一维度得分。"""
    name: str = ""           # 维度名称，如"技术能力"
    score: int = Field(default=0, ge=0, le=100)  # 明确限制 0-100
    source: Literal["resume", "user_input", "manual"] = "manual"

class Constraint(BaseModel):
    """用户硬约束。"""
    type: str = ""           # "location" | "salary_min" | "degree" | "work_mode"
    value: str = ""
    label: str = ""          # 展示用中文标签

class Preference(BaseModel):
    """用户偏好。"""
    type: str = ""           # "industry" | "role_type" | "company_size" | "growth_speed"
    value: str = ""
    label: str = ""

class ProfileData(BaseModel):
    # ... 现有字段保留 ...

    # 新增字段
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)           # 标签云，如 ["Python", "后端", "应届生"]
    strengths: list[str] = Field(default_factory=list)      # 优势，如 ["算法基础扎实", "有实习经历"]
    weaknesses: list[str] = Field(default_factory=list)     # 短板，如 ["无大规模系统经验"]
    constraints: list[Constraint] = Field(default_factory=list)
    preferences: list[Preference] = Field(default_factory=list)
```

**默认值策略**：所有新增字段默认空列表，保证向后兼容。老数据读取时不会报错。

### 1.2 数据库无需改表

新增字段都在 `ProfileData` 的 JSON blob 里存取（`profiles.profile_json` 和 `profile_parses.confirmed_profile_json`），不需要新增数据库列。

---

## 2. API 层

### 2.1 已有接口（保留）

- `POST /api/v2/profiles` — 保存完整画像（简历解析后走这个）
- `GET /api/v2/profiles/me` — 读取画像

### 2.2 新增 PATCH 接口（MVP 必选）

前端"补充信息"编辑时，拿不到原始 `document` 和 `parse_meta`，无法复用 POST。必须提供局部更新：

```python
PATCH /api/v2/profiles/me/profile-data
Body: Partial[ProfileData]   # 只传要改的字段，如 { "preferences": [...] }
```

**后端行为**：
1. 读取当前 `profiles` 行的 `profile_json`
2. 用请求体中的字段覆盖对应属性
3. 更新 `profile_json` 和 `updated_at`
4. **不**写入 `profile_parses`（这不是一次新的解析，只是用户补充信息）

---

## 3. 前端层

### 3.1 `ProfileReadonlyView.tsx` 重构

**数据流调整**：`ProfileReadonlyView.tsx` 直接接收 `V2ProfileData`（来自 `useProfileDataV2` 或 `GET /api/v2/profiles/me`），**不再经过 v1 adapter 转换**。新增字段放在 v2 根上，adapter 会丢掉它们。

去掉所有推荐相关内容，拆成以下展示块：

| 区块 | 内容 | 数据来源 |
|------|------|----------|
| **画像摘要** | 姓名、学校、专业、来源标签、更新时间 | `profile.name`, `profile.education` |
| **能力维度** | 进度条列表（dimension_scores），本版不做雷达图 | `profile.dimension_scores` |
| **标签** | 标签云（tags） | `profile.tags` |
| **优势 / 短板** | 两列卡片 | `profile.strengths`, `profile.weaknesses` |
| **经历时间线** | 教育、实习、项目（复用现有） | `profile.education`, `profile.internships`, `profile.projects` |
| **偏好 / 约束** | 地域、薪资、工作模式、行业偏好等 | `profile.constraints`, `profile.preferences` |

### 3.2 去掉的内容

- ❌ "岗位匹配摘要" 卡片（matchRate、gapCount、weeks）
- ❌ "推荐方向" 区块
- ❌ "核心分析" 中的"推荐下一步"
- ❌ "推荐 Banner"
- ❌ 所有 `hasGoal`、`primaryGoal`、`gp`（graph_position）相关展示

### 3.3 新增编辑入口

在画像页面顶部或底部增加"补充信息"按钮，弹出表单让用户填写：

| 字段 | 类型 | 示例 |
|------|------|------|
| 兴趣方向 | 多选 | "AI/ML", "后端", "产品" |
| 期望工作城市 | 多选 | "北京", "上海", "远程" |
| 最低薪资期望 | 数字 | 15000 |
| 工作模式偏好 | 单选 | "全职", "实习", "远程" |
| 公司规模偏好 | 多选 | "大厂", "独角兽", "初创" |
| 成长速度偏好 | 单选 | "快速晋升", "稳健成长", "work-life balance" |
| 自我评价优势 | 文本 | 500 字上限 |
| 自我评价短板 | 文本 | 500 字上限 |

**表单验证规则**：
- 薪资期望：正整数，可选填
- 城市 / 行业 / 公司规模：预设选项多选，枚举值写死不开放自由文本（避免脏数据）
- 自我评价：500 字上限

表单提交后：
1. 把用户填写的信息合并到现有 `ProfileData`
2. 走 `PATCH /api/v2/profiles/me/profile-data` 保存

> **本版不做任何 LLM 调用**。`dimension_scores`、`tags`、`strengths`、`weaknesses` 由用户手动填写或空态展示。

---

## 4. 实施步骤

### Step 1: 后端 Schema 扩展
- 修改 `backend2/schemas/profile.py`，新增子模型和字段
- 更新 `ProfileData` 的 `to_dict()` 确保序列化正确

### Step 2: 前端类型同步
- 更新 `frontend-v2/src/types/profile-v2.ts`（或 `profile.ts`），新增前端类型

### Step 3: 前端页面重构
- 重写 `ProfileReadonlyView.tsx`：去掉推荐逻辑，拆开展示块
- 新增 `ProfileEditForm.tsx`：补充信息表单
- 更新 `ProfilePage.tsx`：去掉 `recommendations` prop 和轮询逻辑

### Step 4: 删 v1 hack
1. 先确认无其他调用方：
   ```bash
   grep -r "_auto_locate_on_graph" backend2/ --include="*.py"
   # 确认只有 service.py 一处调用，再删除
   ```
2. 删除 `backend2/services/profile/service.py` 中触发 `_auto_locate_on_graph` 的后台线程代码（lines 117-138）

---

## 5. 验收标准

- [ ] Profile 页面不再显示"岗位匹配度"、"推荐方向"、"成长路径"
- [ ] Profile 页面展示：画像摘要、能力维度、标签、优势/短板、经历时间线、偏好/约束
- [ ] 用户可以点击"补充信息"编辑偏好、约束、自我评价
- [ ] 保存后刷新页面，补充的信息正确展示
- [ ] backend2 不再 import `backend.services.graph.locator`
- [ ] 老用户（已有 profile_json）访问页面不报错，新增字段显示为空/默认值
