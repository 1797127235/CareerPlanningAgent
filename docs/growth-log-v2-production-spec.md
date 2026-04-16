# 成长档案 v2 上生产 — 替换旧版

> **前置**：已有 v2 demo 在 `/growth-log-v2`（纯 mock 数据），效果用户满意
> **目标**：把 v2 接入真实后端，让它成为 `/growth-log` 的唯一版本，删除旧页
> **完整设计文档**：`docs/growth-log-v2-spec.md`
> **Demo spec**：`docs/growth-log-v2-demo-spec.md`

---

## §0 范围

这次要做 3 件事：

1. **后端**：新建 `GrowthEntry` 表 + CRUD API + AI 建议端点 + 接入报告系统
2. **前端**：把 v2 页面从 mock 切到真实 API，保留旧数据（项目/投递/面试）在时间线里混排
3. **切换**：`/growth-log` 指向 v2 页面，删除旧 `GrowthLogPage.tsx` 和不再使用的组件

---

## §1 后端实施

### §1.1 新增 `GrowthEntry` ORM 模型

**文件**：`backend/db_models.py` 末尾追加：

```python
class GrowthEntry(Base):
    """统一成长档案记录 — 学习笔记 / 面试复盘 / 项目记录 / 计划"""
    __tablename__ = "growth_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)  # project|interview|learning|null
    tags: Mapped[list] = mapped_column(JSON, default=list)

    # 面试/项目的结构化数据；学习笔记为 None
    structured_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # 计划
    is_plan: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(16), default="done")  # done|pending|dropped
    due_type: Mapped[str | None] = mapped_column(String(16), nullable=True)  # daily|weekly|monthly|custom
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # AI 建议
    ai_suggestions: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # 关联（可选）
    linked_project_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("project_records.id"), nullable=True)
    linked_application_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("job_applications.id"), nullable=True)

    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
```

表会由 `init_db()` 自动创建（SQLAlchemy `create_all`），不需要单独 migration 脚本。

### §1.2 新增 CRUD 路由

**文件**：`backend/routers/growth_log.py` 末尾追加（不要改已有函数）：

```python
# ── GrowthEntry v2: 统一记录 ────────────────────────────────────────

class GrowthEntryCreate(BaseModel):
    content: str
    category: str | None = None
    tags: list[str] = []
    structured_data: dict | None = None
    is_plan: bool = False
    due_type: str | None = None
    due_at: datetime | None = None
    linked_project_id: int | None = None
    linked_application_id: int | None = None
    model_config = {"extra": "ignore"}


class GrowthEntryUpdate(BaseModel):
    content: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    structured_data: dict | None = None
    status: str | None = None         # done|pending|dropped
    due_type: str | None = None
    due_at: datetime | None = None
    model_config = {"extra": "ignore"}


@router.get("/entries")
def list_entries(
    status: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列表。默认倒序按 created_at。"""
    q = db.query(GrowthEntry).filter(GrowthEntry.user_id == user.id)
    if status:
        q = q.filter(GrowthEntry.status == status)
    if category:
        q = q.filter(GrowthEntry.category == category)
    if tag:
        # tags 是 JSON，SQLite 里用 LIKE（不做严格匹配，demo 级够用）
        q = q.filter(GrowthEntry.tags.like(f'%"{tag}"%'))
    entries = q.order_by(GrowthEntry.created_at.desc()).limit(200).all()
    return {"entries": [_entry_to_dict(e) for e in entries]}


@router.post("/entries", status_code=201)
def create_entry(
    req: GrowthEntryCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    entry = GrowthEntry(
        user_id=user.id,
        content=req.content,
        category=req.category,
        tags=req.tags,
        structured_data=req.structured_data,
        is_plan=req.is_plan,
        status="pending" if req.is_plan else "done",
        due_type=req.due_type,
        due_at=req.due_at,
        linked_project_id=req.linked_project_id,
        linked_application_id=req.linked_application_id,
        completed_at=None if req.is_plan else now,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _entry_to_dict(entry)


@router.patch("/entries/{entry_id}")
def update_entry(
    entry_id: int,
    req: GrowthEntryUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = db.query(GrowthEntry).filter(
        GrowthEntry.id == entry_id, GrowthEntry.user_id == user.id
    ).first()
    if not entry:
        raise HTTPException(404, "记录不存在")

    data = req.model_dump(exclude_none=True)
    # 状态改成 done 时自动设 completed_at
    if data.get("status") == "done" and entry.status != "done":
        entry.completed_at = datetime.now(timezone.utc)
    for k, v in data.items():
        setattr(entry, k, v)
    db.commit()
    db.refresh(entry)
    return _entry_to_dict(entry)


@router.delete("/entries/{entry_id}", status_code=204)
def delete_entry(
    entry_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = db.query(GrowthEntry).filter(
        GrowthEntry.id == entry_id, GrowthEntry.user_id == user.id
    ).first()
    if not entry:
        raise HTTPException(404, "记录不存在")
    db.delete(entry)
    db.commit()


def _entry_to_dict(e: GrowthEntry) -> dict:
    return {
        "id": e.id,
        "content": e.content,
        "category": e.category,
        "tags": e.tags or [],
        "structured_data": e.structured_data,
        "is_plan": e.is_plan,
        "status": e.status,
        "due_type": e.due_type,
        "due_at": e.due_at.isoformat() if e.due_at else None,
        "ai_suggestions": e.ai_suggestions,
        "linked_project_id": e.linked_project_id,
        "linked_application_id": e.linked_application_id,
        "completed_at": e.completed_at.isoformat() if e.completed_at else None,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }
```

别忘了在文件顶部 import：
```python
from backend.db_models import GrowthEntry
```

### §1.3 AI 建议端点 + skill

**文件 1**：`backend/skills/growth-suggest/SKILL.md`（新建目录 + 文件）

```markdown
---
name: growth-suggest
description: 针对一条成长档案记录，给 1-3 条具体可执行的建议
model: fast
temperature: 0.3
max_tokens: 400
output: json
---

## System

你是学生的学习/求职顾问。针对一条成长档案记录，给 1-3 条**具体可执行**的建议。

**硬约束**：
- 必须具体（"复习 RDB vs AOF 的触发机制"），不能抽象（"加强 Redis 学习"）
- 必须可执行（有动作、有范围），不能是空话
- 数量 1-3 条，宁缺毋滥
- 结合用户目标方向给建议（目标是后端就别推前端的学习）

**面试复盘特殊处理**：
- 针对每个答得不好的问题给具体补强建议
- 可以推荐 LeetCode 题目/博客文章/具体概念复习

**输出格式**（严格 JSON，不要 markdown 代码块）：
```json
{"suggestions": [{"text": "...", "category": "learning"}]}
```

category 取值：`learning` | `project` | `interview`

## User

**用户目标方向**：{target_label}

**用户已有技能**：{user_skills}

**这条记录**：
类型：{entry_category}
内容：{entry_content}
结构化数据：{structured_data}

请给 1-3 条针对性建议。
```

**文件 2**：在 `growth_log.py` 新增端点：

```python
@router.post("/entries/{entry_id}/ai-suggest")
def ai_suggest(
    entry_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from backend.skills import invoke_skill
    from backend.db_models import Profile, CareerGoal

    entry = db.query(GrowthEntry).filter(
        GrowthEntry.id == entry_id, GrowthEntry.user_id == user.id
    ).first()
    if not entry:
        raise HTTPException(404, "记录不存在")

    # 取画像 + 目标
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    goal = db.query(CareerGoal).filter(
        CareerGoal.user_id == user.id, CareerGoal.is_active == True
    ).first()

    profile_data = json.loads(profile.profile_json or "{}") if profile else {}
    user_skills = [s.get("name", "") for s in profile_data.get("skills", []) if s.get("name")]

    try:
        result = invoke_skill(
            "growth-suggest",
            target_label=goal.target_label if goal else "未选方向",
            user_skills=", ".join(user_skills[:20]) or "无",
            entry_category=entry.category or "note",
            entry_content=entry.content,
            structured_data=json.dumps(entry.structured_data or {}, ensure_ascii=False),
        )
        suggestions = result.get("suggestions", []) if isinstance(result, dict) else []
    except Exception as e:
        logger.warning("ai-suggest failed: %s", e)
        suggestions = []

    # 写回 entry
    entry.ai_suggestions = suggestions
    db.commit()
    return {"suggestions": suggestions}
```

### §1.4 接入报告系统

**文件**：`backend/services/report/summarize.py`

在 `_build_milestones()` 函数末尾（`return items` 之前）新增：

```python
# ── GrowthEntry (unified log) ──
try:
    from backend.db_models import GrowthEntry
    entries = (
        db.query(GrowthEntry)
        .filter(
            GrowthEntry.user_id == user_id,
            GrowthEntry.status == "done",
            GrowthEntry.created_at >= since,
        )
        .order_by(GrowthEntry.created_at.desc())
        .limit(20)
        .all()
    )
    cat_map = {
        "project": "project_progress",
        "interview": "interview",
        "learning": "learning_note",
    }
    for entry in entries:
        counter += 1
        sd = entry.structured_data or {}
        if entry.category == "interview":
            title = f"{sd.get('company','')} {sd.get('round','面试')}".strip() or entry.content[:60]
            detail = entry.content[:200]
            skills = []
        elif entry.category == "project":
            title = sd.get("name", entry.content[:40])
            detail = sd.get("description", entry.content)[:200]
            skills = sd.get("skills_used", [])
        else:
            title = entry.content[:60]
            detail = entry.content[:200]
            skills = []

        items.append({
            "id": f"M-{counter:03d}",
            "date_iso": _iso(entry.completed_at or entry.created_at),
            "source": f"growth_entry:{entry.id}",
            "category": cat_map.get(entry.category, "note"),
            "title": title,
            "detail": detail,
            "skills_touched": skills,
        })
except Exception as e:
    logger.warning("_build_milestones GrowthEntry failed: %s", e)
```

**另**：`_latest_user_activity_time()` 里加一条查询：
```python
db.query(func.max(GrowthEntry.updated_at)).filter(GrowthEntry.user_id == user_id),
```

确保新记录能触发报告缓存失效。

---

## §2 前端实施

### §2.1 新增真实 API 客户端

**文件**：`frontend/src/api/growthEntries.ts`（新建）

```typescript
import { rawFetch } from './client'

const BASE = '/api/growth-log'

export interface InterviewQA { q: string; a: string }

export interface InterviewData {
  company: string
  position: string
  round: string
  questions: InterviewQA[]
  self_rating: 'good' | 'medium' | 'bad'
  result: 'passed' | 'failed' | 'pending'
  reflection?: string
}

export interface ProjectData {
  name: string
  description?: string
  skills_used: string[]
  github_url?: string
  status: 'planning' | 'in_progress' | 'completed'
}

export interface AiSuggestion { text: string; category?: string }

export interface GrowthEntry {
  id: number
  content: string
  category: 'learning' | 'interview' | 'project' | null
  tags: string[]
  structured_data: InterviewData | ProjectData | null
  is_plan: boolean
  status: 'done' | 'pending' | 'dropped'
  due_type: 'daily' | 'weekly' | 'monthly' | 'custom' | null
  due_at: string | null
  completed_at: string | null
  created_at: string
  ai_suggestions: AiSuggestion[] | null
}

export const listEntries = (params?: { status?: string; category?: string; tag?: string }) => {
  const q = new URLSearchParams()
  if (params?.status) q.set('status', params.status)
  if (params?.category) q.set('category', params.category)
  if (params?.tag) q.set('tag', params.tag)
  const qs = q.toString()
  return rawFetch<{ entries: GrowthEntry[] }>(`${BASE}/entries${qs ? '?' + qs : ''}`)
}

export const createEntry = (data: Partial<GrowthEntry>) =>
  rawFetch<GrowthEntry>(`${BASE}/entries`, { method: 'POST', body: JSON.stringify(data) })

export const updateEntry = (id: number, patch: Partial<GrowthEntry>) =>
  rawFetch<GrowthEntry>(`${BASE}/entries/${id}`, { method: 'PATCH', body: JSON.stringify(patch) })

export const deleteEntry = (id: number) =>
  rawFetch<void>(`${BASE}/entries/${id}`, { method: 'DELETE' })

export const aiSuggest = (id: number) =>
  rawFetch<{ suggestions: AiSuggestion[] }>(`${BASE}/entries/${id}/ai-suggest`, { method: 'POST' })
```

### §2.2 改造 mockData.ts → 真实数据

**文件**：`frontend/src/components/growth-log-v2/mockData.ts`

把所有 `mockEntries` 和操作函数删掉，改成用 React Query：

**新增**：`frontend/src/components/growth-log-v2/useEntries.ts`

```typescript
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import {
  listEntries, createEntry, updateEntry, deleteEntry, aiSuggest,
  type GrowthEntry,
} from '@/api/growthEntries'

const QK = ['growth-entries'] as const

export function useGrowthEntries() {
  const qc = useQueryClient()

  const list = useQuery({
    queryKey: QK,
    queryFn: () => listEntries(),
    staleTime: 30_000,
  })

  const add = useMutation({
    mutationFn: (data: Partial<GrowthEntry>) => createEntry(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: QK }),
  })

  const patch = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<GrowthEntry> }) => updateEntry(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: QK }),
  })

  const remove = useMutation({
    mutationFn: (id: number) => deleteEntry(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: QK }),
  })

  const requestAi = useMutation({
    mutationFn: (id: number) => aiSuggest(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: QK }),
  })

  return {
    entries: list.data?.entries ?? [],
    loading: list.isLoading,
    error: list.error,
    addEntry: add.mutateAsync,
    updateEntry: (id: number, data: Partial<GrowthEntry>) => patch.mutateAsync({ id, data }),
    deleteEntry: remove.mutateAsync,
    requestAiSuggestions: requestAi.mutateAsync,
  }
}
```

### §2.3 改 GrowthLogV2Page + 子组件

**所有 v2 组件**（`frontend/src/components/growth-log-v2/*`）之前 import `from './mockData'` 的地方，
改为 `from './useEntries'` 或 `from '@/api/growthEntries'`。

**GrowthLogV2Page.tsx** 改造点：
1. 顶部用 `useGrowthEntries()` hook 替代从 mockData 导入
2. 所有 `addEntry` / `updateEntry` / `deleteEntry` 调用改为 await
3. AI 建议按钮改为调 `requestAiSuggestions(id)`
4. 保留原有的 `groupByDate` / `mergeRecords` 逻辑
5. **新增**：把旧数据（ProjectRecord + JobApplication）合并进时间线
   - 调 `listProjects()` 和 `listApplications()`
   - 在时间线里同时显示新 GrowthEntry 和旧 Project/Application
   - 旧数据用现有的 `RecordRow` 或适配成 EntryCard 样式
   - 旧数据**不能删除/编辑**（只读展示），用户要修改需用新建记录

### §2.4 路由切换

**文件**：`frontend/src/App.tsx`

把：
```tsx
<Route path="/growth-log" element={<GrowthLogPage />} />
<Route path="/growth-log-v2" element={<GrowthLogV2Page />} />
```

改为：
```tsx
<Route path="/growth-log" element={<GrowthLogV2Page />} />
<Route path="/growth-log-v2" element={<Navigate to="/growth-log" replace />} />
```

import 里删掉 `GrowthLogPage`，保留 `GrowthLogV2Page`。

### §2.5 删除旧代码

**删除文件**：
- `frontend/src/pages/GrowthLogPage.tsx`

**删除 components/growth-log/ 里不再用的文件**：
- `FilterChips.tsx`（v2 自己有）
- `NewRecordDialog.tsx`
- `RecordRow.tsx`

**保留**（仍被引用或者旧数据展示要用）：
- `GoalBar.tsx`（v2 顶部仍用）
- `ProjectsSection.tsx` / `PursuitsSection.tsx`（`ProjectGraphPage` / `PursuitDetailPage` 可能还在用）
- `GrowthDashboard.tsx`（暂保留，后续 Batch 清理）
- 其他的保留，避免级联报错

先 `grep -r` 确认每个要删的文件没有其他地方 import，再动手。

---

## §3 验收清单

### 后端

1. ☐ `python -c "from backend.db_models import GrowthEntry; print('ok')"` 无错
2. ☐ `python -c "from backend.app import app"` 无错
3. ☐ 起服务 → `POST /api/growth-log/entries` 创建一条记录返回 201
4. ☐ `GET /api/growth-log/entries` 返回列表
5. ☐ `PATCH /api/growth-log/entries/:id` 改状态成功，completed_at 自动填充
6. ☐ `POST /api/growth-log/entries/:id/ai-suggest` 返回 1-3 条建议（或空数组+不报错）
7. ☐ 生成报告 → `summary.milestones` 里出现新的 `source: "growth_entry:..."` 条目

### 前端

1. ☐ 访问 `/growth-log` → 看到 v2 页面
2. ☐ 访问 `/growth-log-v2` → 重定向到 `/growth-log`
3. ☐ 写一条学习笔记 → 发送 → 出现在"今天"组
4. ☐ 刷新页面 → 记录还在（来自后端）
5. ☐ 填面试复盘表单保存 → 面试卡片正确展示问答
6. ☐ 填项目表单保存 → 项目卡片正确展示
7. ☐ 建计划 → pending 区出现；打勾 → 移到时间线
8. ☐ 点 AI 建议 → 显示真实 LLM 返回的建议
9. ☐ AI 建议上点"转为计划" → pending 区新增一条
10. ☐ 旧项目（ProjectRecord）仍在时间线显示（只读）
11. ☐ 旧投递（JobApplication）仍在时间线显示（只读）

### 集成

1. ☐ HomePage 导航到 "去成长日志" 按钮仍能跳转到 `/growth-log`
2. ☐ 侧边栏"成长档案"菜单点击跳到 v2 页面
3. ☐ `npm run build` 无 TypeScript 错误
4. ☐ 报告生成不报错，新记录出现在报告 milestones 里

---

## §4 开工前先回一句

读完 spec 回："文档读完，准备开工"。

**特别注意**：
- 这次是**生产替换**，不是 demo，所有数据要真正存库
- 旧页面 `GrowthLogPage.tsx` 要彻底删掉，不要留两套
- 旧数据（ProjectRecord / JobApplication）继续在时间线里显示，不迁移
- `ProjectGraphPage` 和 `PursuitDetailPage` 的详情页不动，保持可跳转
- AI 建议调 LLM 可能失败/超时，要有 fallback（返回空数组，不让前端报错）

如果哪里不确定，先停下来问。
