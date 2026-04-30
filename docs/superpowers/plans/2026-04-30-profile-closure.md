# 画像闭环重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Profile 页面从"推荐入口"改成"个人画像管理页"，扩展画像数据结构，新增 PATCH 局部更新接口，前端直接消费 v2 原生数据。

**Architecture:** 后端 `ProfileData` 新增 `dimension_scores`、`tags`、`strengths`、`weaknesses`、`constraints`、`preferences` 字段，全部走 JSON blob 存储，不改数据库表。前端 `ProfileReadonlyView.tsx` 直接接收 `V2ProfileData`，去掉所有推荐/图谱相关展示，拆成画像摘要、能力维度、标签、优势短板、经历时间线、偏好约束六个展示块，并新增`ProfileEditForm`供用户补充信息。

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy, React + TypeScript, Tailwind CSS

---

## File Map

| File | Responsibility |
|------|---------------|
| `backend2/schemas/profile.py` | `DimensionScore`, `Constraint`, `Preference` 子模型 + `ProfileData` 扩展 |
| `backend2/routers/profiles.py` | 新增 `PATCH /api/v2/profiles/me/profile-data` 路由 |
| `backend2/services/profile/service.py` | 新增 `patch_profile_data()` 服务函数 |
| `frontend-v2/src/types/profile-v2.ts` | 前端类型同步（新增字段） |
| `frontend-v2/src/api/profiles-v2.ts` | 新增 `patchProfileData()` API 调用 |
| `frontend-v2/src/components/profile-v2/ProfileReadonlyView.tsx` | 重构：去掉推荐逻辑，拆展示块 |
| `frontend-v2/src/components/profile-v2/ProfileEditForm.tsx` | 新建：补充信息表单 |
| `frontend-v2/src/pages/ProfilePage.tsx` | 去掉 recommendations prop 和轮询，接入编辑表单 |

---

### Task 1: 后端 Schema 扩展

**Files:**
- Modify: `backend2/schemas/profile.py`
- Test: `backend2/tests/test_profile_schemas.py` (create if not exists)

- [ ] **Step 1: 新增子模型**

在 `backend2/schemas/profile.py` 的 `Skill` 类下方插入：

```python
class DimensionScore(BaseModel):
    """单一维度得分。"""
    name: str = ""
    score: int = Field(default=0, ge=0, le=100)
    source: Literal["resume", "user_input", "manual"] = "manual"


class Constraint(BaseModel):
    """用户硬约束。"""
    type: str = ""           # "location" | "salary_min" | "degree" | "work_mode"
    value: str = ""
    label: str = ""


class Preference(BaseModel):
    """用户偏好。"""
    type: str = ""           # "industry" | "role_type" | "company_size" | "growth_speed"
    value: str = ""
    label: str = ""
```

- [ ] **Step 2: 扩展 `ProfileData`**

在 `ProfileData` 类末尾（`raw_text` 字段之后）新增：

```python
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)
    preferences: list[Preference] = Field(default_factory=list)
```

- [ ] **Step 3: 写序列化测试**

```python
# backend2/tests/test_profile_schemas.py
from backend2.schemas.profile import ProfileData, DimensionScore, Constraint, Preference

def test_profile_data_with_new_fields():
    data = ProfileData(
        name="张三",
        tags=["Python", "后端"],
        strengths=["算法基础扎实"],
        weaknesses=["无大规模系统经验"],
        dimension_scores=[DimensionScore(name="技术能力", score=75, source="user_input")],
        constraints=[Constraint(type="location", value="北京", label="北京")],
        preferences=[Preference(type="industry", value="互联网", label="互联网")],
    )
    d = data.to_dict()
    assert d["name"] == "张三"
    assert d["tags"] == ["Python", "后端"]
    assert d["dimension_scores"][0]["score"] == 75
    assert d["dimension_scores"][0]["source"] == "user_input"

def test_profile_data_backward_compat():
    """老数据（无新增字段）应能正常反序列化。"""
    data = ProfileData(name="李四")
    assert data.tags == []
    assert data.dimension_scores == []
```

- [ ] **Step 4: 运行测试**

Run: `python -m pytest backend2/tests/test_profile_schemas.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend2/schemas/profile.py backend2/tests/test_profile_schemas.py
git commit -m "feat(profile): extend ProfileData with dimension_scores, tags, strengths, weaknesses, constraints, preferences"
```

---

### Task 2: PATCH API 实现

**Files:**
- Modify: `backend2/services/profile/service.py`
- Modify: `backend2/routers/profiles.py`
- Test: `backend2/tests/test_profile_patch.py` (create)

- [ ] **Step 1: 新增 `ProfileDataPatch` schema**

在 `backend2/schemas/profile.py` 末尾（`SaveProfileResponse` 之后）添加：

```python
class ProfileDataPatch(BaseModel):
    """允许局部更新的字段子集。"""
    dimension_scores: list[DimensionScore] | None = None
    tags: list[str] | None = None
    strengths: list[str] | None = None
    weaknesses: list[str] | None = None
    constraints: list[Constraint] | None = None
    preferences: list[Preference] | None = None
```

- [ ] **Step 2: 新增 `patch_profile_data` 服务函数**

在 `backend2/services/profile/service.py` 末尾（`get_my_profile` 函数之后）添加：

```python
from fastapi import HTTPException
from backend2.schemas.profile import ProfileDataPatch


def patch_profile_data(
    db: Session,
    user_id: int,
    patch: ProfileDataPatch,
) -> ProfileData:
    """局部更新用户画像，不生成新的 parse 快照。"""
    from backend2.services.profile.resolver import resolve_profile_context

    profile_data, profile_id, _parse_id = resolve_profile_context(db, user_id)
    if profile_id is None:
        raise HTTPException(status_code=404, detail="画像不存在")

    # 读取当前 JSON
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    current_json = json.loads(profile.profile_json or "{}")

    # 只覆盖请求中提供的字段
    patch_dict = patch.model_dump(exclude_unset=True, mode="json")
    current_json.update(patch_dict)

    # 写回
    # 写回 profiles 主表
    profile.profile_json = json.dumps(current_json, ensure_ascii=False)

    # 同步更新当前 active_parse 的 confirmed_profile_json（resolver 优先读这里）
    if profile.active_parse_id:
        parse_snapshot = db.query(ProfileParse).filter(
            ProfileParse.id == profile.active_parse_id
        ).first()
        if parse_snapshot:
            parse_snapshot.confirmed_profile_json = profile.profile_json

    db.commit()
    db.refresh(profile)

    logger.info("画像局部更新: user_id=%d, fields=%s", user_id, list(patch_dict.keys()))
    return ProfileData.model_validate(current_json)
```

- [ ] **Step 2: 新增路由**

在 `backend2/routers/profiles.py` 中，在 `get_my_profile` 路由之后添加：

```python
from backend2.services.profile.service import (
    parse_resume_preview,
    save_profile,
    get_my_profile,
    patch_profile_data,
)
from backend2.schemas.profile import ProfileDataPatch

@router.patch("/me/profile-data", response_model=ProfileData)
def patch_my_profile(
    patch: ProfileDataPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """局部更新当前用户画像（补充信息）。"""
    return patch_profile_data(db, current_user.id, patch)
```

- [ ] **Step 3: 写路由测试**

```python
# backend2/tests/test_profile_patch.py
from fastapi.testclient import TestClient
from backend2.app import app

client = TestClient(app)

def test_patch_profile_unauthorized():
    r = client.patch("/api/v2/profiles/me/profile-data", json={"tags": ["Python"]})
    assert r.status_code == 401
```

> 注：完整的 PATCH 集成测试需要认证和 DB setup，如果测试基础设施不完善，可只做手动验证（见 Step 4）。

- [ ] **Step 4: 手动验证**

1. 启动 backend2: `python -m uvicorn backend2.app:app --port 8002`
2. 先登录获取 JWT
3. `curl -X PATCH http://localhost:8002/api/v2/profiles/me/profile-data \
   -H "Authorization: Bearer $TOKEN" \
   -H "Content-Type: application/json" \
   -d '{"tags": ["Python", "后端"], "strengths": ["算法基础扎实"]}'`
4. Expected: 返回更新后的完整 ProfileData，tags 和 strengths 已更新

- [ ] **Step 5: Commit**

```bash
git add backend2/services/profile/service.py backend2/routers/profiles.py backend2/tests/test_profile_patch.py
git commit -m "feat(profile): add PATCH /profiles/me/profile-data for partial updates"
```

---

### Task 3: 前端类型同步

**Files:**
- Modify: `frontend-v2/src/types/profile-v2.ts`
- Test: TypeScript compiler (`tsc --noEmit`)

- [ ] **Step 1: 检查现有类型文件位置**

Run: `ls frontend-v2/src/types/`
确定 profile 类型定义在 `profile.ts` 还是 `profile-v2.ts`。

- [ ] **Step 2: 新增前端类型**

```typescript
// 在 profile / profile-v2 类型文件中追加

export interface DimensionScore {
  name: string;
  score: number;          // 0-100
  source: "resume" | "user_input" | "manual";
}

export interface Constraint {
  type: string;
  value: string;
  label: string;
}

export interface Preference {
  type: string;
  value: string;
  label: string;
}

// 扩展 V2ProfileData
export interface V2ProfileData {
  // ... 现有字段保留 ...
  dimension_scores?: DimensionScore[];
  tags?: string[];
  strengths?: string[];
  weaknesses?: string[];
  constraints?: Constraint[];
  preferences?: Preference[];
}
```

- [ ] **Step 3: 运行类型检查**

Run: `cd frontend-v2 && npx tsc --noEmit`
Expected: 无新增类型错误（原有错误可忽略）

- [ ] **Step 4: Commit**

```bash
git add frontend-v2/src/types/profile*.ts
git commit -m "feat(types): add DimensionScore, Constraint, Preference to profile types"
```

---

### Task 4: 前端 API 层

**Files:**
- Modify: `frontend-v2/src/api/profiles-v2.ts`
- Modify: `frontend-v2/src/api/index.ts`

- [ ] **Step 1: 新增 `patchProfileData` 函数**

在 `frontend-v2/src/api/profiles-v2.ts` 中添加：

```typescript
import { v2RawFetch } from "./index";
import type { V2ProfileData } from "@/types/profile-v2";

export interface ProfileDataPatch {
  dimension_scores?: Array<{ name: string; score: number; source: string }>;
  tags?: string[];
  strengths?: string[];
  weaknesses?: string[];
  constraints?: Array<{ type: string; value: string; label: string }>;
  preferences?: Array<{ type: string; value: string; label: string }>;
}

export async function patchProfileData(patch: ProfileDataPatch): Promise<V2ProfileData> {
  const data = await v2RawFetch("/profiles/me/profile-data", {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
  return data as V2ProfileData;
}
```

- [ ] **Step 2: 在 `frontend-v2/src/api/index.ts` 中 export**

```typescript
export { patchProfileData } from "./profiles-v2";
```

- [ ] **Step 3: Commit**

```bash
git add frontend-v2/src/api/profiles-v2.ts frontend-v2/src/api/index.ts
git commit -m "feat(api): add patchProfileData for partial profile updates"
```

---

### Task 5: 重写 `ProfileReadonlyView.tsx`（v2 画像结构）

**策略**：不增量删改旧代码，直接以 v2 `V2ProfileData` 结构重写。保留文件名以减少 import 改动。

**Files:**
- Rewrite: `frontend-v2/src/components/profile-v2/ProfileReadonlyView.tsx`

- [ ] **Step 1: 新 Props 接口**

```typescript
interface Props {
  data: V2ProfileData;
  onDelete?: () => Promise<void>;
  onSaveEducation?: (data: Education) => Promise<void>;
  onSaveSkills?: (data: Skill[]) => Promise<void>;
  onSaveInternships?: (data: Internship[]) => Promise<void>;
  onSaveProjects?: (data: Array<string | Record<string, unknown>>) => Promise<void>;
  onOpenEdit?: () => void;
}
```

- [ ] **Step 2: 重写骨架**

按以下顺序组织页面（从上到下）：

1. **Header**：姓名 + 学校/专业 + 来源标签 + 更新时间
2. **画像摘要卡片**：一句话简介（可由用户手动填写，暂无则空态）
3. **能力维度**：进度条列表，空态不展示
4. **标签云**：空态不展示
5. **优势 / 短板**：左右两栏卡片
6. **技能列表**：两列（技能名 + 当前水平），无 gap/目标/状态逻辑
7. **经历时间线**：教育、实习、项目，无"职业相关性"标签
8. **偏好与约束**：空态不展示
9. **底部操作栏**：补充信息按钮 + 重置画像按钮

- [ ] **Step 3: 保留可复用子组件**

从旧代码中提取以下子组件（如有）：
- `Card` wrapper
- `Kicker`
- 教育/实习/项目编辑表单（EducationEditForm、SkillsEditForm 等）
- 删除确认弹窗

其余推荐/图谱相关代码全部丢弃。

- [ ] **Step 4: Commit**

```bash
git add frontend-v2/src/components/profile-v2/ProfileReadonlyView.tsx
git commit -m "feat(profile): rewrite ProfileReadonlyView with v2 profile structure"
```

---

### Task 8: `ProfileEditForm.tsx`

**Files:**
- Create: `frontend-v2/src/components/profile-v2/ProfileEditForm.tsx`

- [ ] **Step 1: 创建表单组件**

```tsx
import { useState } from "react";
import type { V2ProfileData } from "@/types/profile-v2";

interface Props {
  open: boolean;
  onClose: () => void;
  initialData: V2ProfileData;
  onSave: (patch: Partial<V2ProfileData>) => Promise<void>;
}

const CITY_OPTIONS = ["北京", "上海", "深圳", "杭州", "广州", "成都", "远程"];
const INDUSTRY_OPTIONS = ["互联网", "AI/ML", "金融科技", "企业服务", "游戏", "新能源"];
const COMPANY_OPTIONS = ["大厂", "独角兽", "外企", "国企", "初创"];
const GROWTH_OPTIONS = [
  { value: "fast", label: "快速晋升" },
  { value: "steady", label: "稳健成长" },
  { value: "balance", label: "Work-life balance" },
];

export default function ProfileEditForm({ open, onClose, initialData, onSave }: Props) {
  const [tags, setTags] = useState(initialData.tags?.join(", ") ?? "");
  const [strengths, setStrengths] = useState(initialData.strengths?.join("\n") ?? "");
  const [weaknesses, setWeaknesses] = useState(initialData.weaknesses?.join("\n") ?? "");
  const [cities, setCities] = useState<string[]>(
    initialData.constraints?.filter((c) => c.type === "location").map((c) => c.value) ?? []
  );
  const [industries, setIndustries] = useState<string[]>(
    initialData.preferences?.filter((p) => p.type === "industry").map((p) => p.value) ?? []
  );
  const [companySizes, setCompanySizes] = useState<string[]>(
    initialData.preferences?.filter((p) => p.type === "company_size").map((p) => p.value) ?? []
  );
  const [growth, setGrowth] = useState(
    initialData.preferences?.find((p) => p.type === "growth_speed")?.value ?? ""
  );
  const [salary, setSalary] = useState(
    initialData.constraints?.find((c) => c.type === "salary_min")?.value ?? ""
  );

  const handleSubmit = async () => {
    const patch: Partial<V2ProfileData> = {
      tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
      strengths: strengths.split("\n").map((s) => s.trim()).filter(Boolean),
      weaknesses: weaknesses.split("\n").map((w) => w.trim()).filter(Boolean),
      constraints: [
        ...cities.map((c) => ({ type: "location", value: c, label: c })),
        ...(salary ? [{ type: "salary_min", value: salary, label: `${salary}元/月` }] : []),
      ],
      preferences: [
        ...industries.map((i) => ({ type: "industry", value: i, label: i })),
        ...companySizes.map((c) => ({ type: "company_size", value: c, label: c })),
        ...(growth ? [{ type: "growth_speed", value: growth, label: GROWTH_OPTIONS.find((g) => g.value === growth)?.label ?? growth }] : []),
      ],
    };
    await onSave(patch);
    onClose();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl p-6 w-full max-w-lg max-h-[80vh] overflow-y-auto">
        <h2 className="text-lg font-semibold mb-4">补充画像信息</h2>

        {/* 标签 */}
        <div className="mb-4">
          <label className="block text-sm mb-1">标签（逗号分隔）</label>
          <input
            className="w-full border rounded px-3 py-2"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="Python, 后端, 应届生"
          />
        </div>

        {/* 优势 */}
        <div className="mb-4">
          <label className="block text-sm mb-1">自我评价优势（每行一条，500字上限）</label>
          <textarea
            className="w-full border rounded px-3 py-2 h-20"
            value={strengths}
            onChange={(e) => {
              if (e.target.value.length <= 500) setStrengths(e.target.value);
            }}
          />
        </div>

        {/* 短板 */}
        <div className="mb-4">
          <label className="block text-sm mb-1">自我评价短板（每行一条，500字上限）</label>
          <textarea
            className="w-full border rounded px-3 py-2 h-20"
            value={weaknesses}
            onChange={(e) => {
              if (e.target.value.length <= 500) setWeaknesses(e.target.value);
            }}
          />
        </div>

        {/* 城市 */}
        <div className="mb-4">
          <label className="block text-sm mb-1">期望工作城市</label>
          <div className="flex flex-wrap gap-2">
            {CITY_OPTIONS.map((c) => (
              <button
                key={c}
                type="button"
                className={`px-3 py-1 rounded-full text-sm border ${cities.includes(c) ? "bg-amber-700 text-white" : ""}`}
                onClick={() => setCities((prev) => prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c])}
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        {/* 行业 */}
        <div className="mb-4">
          <label className="block text-sm mb-1">感兴趣的行业</label>
          <div className="flex flex-wrap gap-2">
            {INDUSTRY_OPTIONS.map((i) => (
              <button
                key={i}
                type="button"
                className={`px-3 py-1 rounded-full text-sm border ${industries.includes(i) ? "bg-amber-700 text-white" : ""}`}
                onClick={() => setIndustries((prev) => prev.includes(i) ? prev.filter((x) => x !== i) : [...prev, i])}
              >
                {i}
              </button>
            ))}
          </div>
        </div>

        {/* 公司规模 */}
        <div className="mb-4">
          <label className="block text-sm mb-1">公司规模偏好</label>
          <div className="flex flex-wrap gap-2">
            {COMPANY_OPTIONS.map((c) => (
              <button
                key={c}
                type="button"
                className={`px-3 py-1 rounded-full text-sm border ${companySizes.includes(c) ? "bg-amber-700 text-white" : ""}`}
                onClick={() => setCompanySizes((prev) => prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c])}
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        {/* 成长速度 */}
        <div className="mb-4">
          <label className="block text-sm mb-1">成长速度偏好</label>
          <select
            className="w-full border rounded px-3 py-2"
            value={growth}
            onChange={(e) => setGrowth(e.target.value)}
          >
            <option value="">请选择</option>
            {GROWTH_OPTIONS.map((g) => (
              <option key={g.value} value={g.value}>{g.label}</option>
            ))}
          </select>
        </div>

        {/* 薪资 */}
        <div className="mb-4">
          <label className="block text-sm mb-1">最低薪资期望（元/月，可选）</label>
          <input
            type="number"
            min={0}
            className="w-full border rounded px-3 py-2"
            value={salary}
            onChange={(e) => setSalary(e.target.value)}
            placeholder="15000"
          />
        </div>

        <div className="flex gap-3 mt-6">
          <button onClick={onClose} className="flex-1 py-2 rounded border">取消</button>
          <button onClick={handleSubmit} className="flex-1 py-2 rounded bg-amber-700 text-white">保存</button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend-v2/src/components/profile-v2/ProfileEditForm.tsx
git commit -m "feat(profile): add ProfileEditForm for user-supplied profile info"
```

---

### Task 9: `ProfilePage.tsx` 接入 + 删 v1 hack

**Files:**
- Modify: `frontend-v2/src/pages/ProfilePage.tsx`
- Modify: `backend2/services/profile/service.py`

- [ ] **Step 1: ProfilePage 清理 + 接入编辑表单**

**先删推荐相关代码**：

删除以下 import / state / hook / 变量：
- `useRecommendations`
- `fetchRecommendations`
- `setCareerGoal`
- `showChangeGoalConfirm`
- `goal` / `hasGoal` / `visibleRecs`
- 更换目标方向弹窗相关 state

删除传给 `ProfileReadonlyView` 的以下 props：
- `onReport`
- `onSetGoal`
- `onChangeGoal`
- `recommendations`

**再接入编辑表单**：
1. import `ProfileEditForm` 和 `patchProfileData`
2. 新增 `editOpen` state
3. 在 `ProfileReadonlyView` 的 props 中加入 `onOpenEdit={() => setEditOpen(true)}`
4. 渲染 `ProfileEditForm`：

```tsx
<ProfileEditForm
  open={editOpen}
  onClose={() => setEditOpen(false)}
  initialData={profileData}
  onSave={async (patch) => {
    await patchProfileData(patch);
    await refetch();   // 重新拉取 profile 数据
  }}
/>
```

5. 去掉 `recommendations` prop 和轮询逻辑（如果有的话）

- [ ] **Step 2: 删 v1 hack**

```bash
grep -r "_auto_locate_on_graph" backend2/ --include="*.py"
# 确认只有 service.py 一处调用
```

删除 `backend2/services/profile/service.py` lines 117-138（`try: import threading ... except Exception: logger.exception` 整个块）。

- [ ] **Step 3: 验证**

1. 启动 backend2 + frontend
2. 打开 Profile 页面，确认无推荐/匹配相关内容
3. 点击"补充信息"，填写标签、优势、城市、行业、薪资
4. 保存，确认页面正确展示新数据
5. 检查 backend2 日志，确认没有 "后台推荐生成" 相关日志

- [ ] **Step 4: Commit**

```bash
git add frontend-v2/src/pages/ProfilePage.tsx backend2/services/profile/service.py
git commit -m "feat(profile): wire up ProfileEditForm, remove v1 graph locator hack"
```

---

## 验收标准（复用 Spec）

- [ ] Profile 页面不再显示"岗位匹配度"、"推荐方向"、"成长路径"
- [ ] Profile 页面展示：画像摘要、能力维度、标签、优势/短板、经历时间线、偏好/约束
- [ ] 用户可以点击"补充信息"编辑偏好、约束、自我评价
- [ ] 保存后刷新页面，补充的信息正确展示
- [ ] backend2 不再 import `backend.services.graph.locator`
- [ ] 老用户（已有 profile_json）访问页面不报错，新增字段显示为空/默认值
