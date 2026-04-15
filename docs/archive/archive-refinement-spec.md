# 档案精修功能 - 实现规范

> **目标**：建立"报告诊断 → 学生自主补足 → 档案升级 → 报告通过"的完整闭环
>
> **项目根目录**：`C:\Users\liu\Desktop\CareerPlanningAgent`
>
> **启动命令**：
> - 后端：`python -m uvicorn backend.app:app --reload`
> - 前端：`cd frontend && npm run dev`

---

## 一、功能全景

### 现状
报告页已有「档案体检」模块（`data.diagnosis`），能识别学生项目描述的三类问题：
- 缺少量化数据（无数字）
- 缺少成果描述（无"提升/降低/支撑"类动词）
- 描述过于简短（<30字）
- 只说"参与"未说明职责

诊断卡片显示：`亮点` + `差一步` + `建议补充`（由 LLM 生成参考格式）

### 本次要做的
1. 诊断卡片加「去补充」按钮 → 跳转到成长档案的新 Tab「档案精修」
2. 成长档案删除现有的「学习」Tab，新增「档案精修」Tab
3. 档案精修面板展示所有需要补完的项目，学生自己填写真实数据
4. 保存时更新对应数据源（ProjectRecord 或 profile_json）
5. 再次生成报告时，精修过的项目自动变"通过"状态

### 核心原则
- **AI 不替学生写**：AI 只指出问题和给参考格式，学生填真实数据
- **温和措辞**：用"还差一点"、"档案精修"，不用"待完善"、"问题"
- **达标门槛不追求完美**：有数字 + 长度>50字 + 有成果动词 = pass

---

## 二、后端实现

### 2.1 新增 API 端点

**文件**：`backend/routers/profiles.py`

添加新端点：

```python
from pydantic import BaseModel

class UpdateProjectDescBody(BaseModel):
    description: str

@router.patch("/me/projects/{proj_index}")
def update_profile_project(
    proj_index: int,
    body: UpdateProjectDescBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新 profile_json.projects[index] 的项目描述（简历提取的项目）"""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(404, "未找到画像")
    
    import json
    data = json.loads(profile.profile_json or "{}")
    projects = data.get("projects", [])
    
    if proj_index < 0 or proj_index >= len(projects):
        raise HTTPException(400, "项目索引越界")
    
    # projects[i] 可能是 str 或 dict
    current = projects[proj_index]
    if isinstance(current, str):
        projects[proj_index] = body.description
    elif isinstance(current, dict):
        projects[proj_index] = {**current, "description": body.description}
    
    data["projects"] = projects
    profile.profile_json = json.dumps(data, ensure_ascii=False)
    db.commit()
    
    return {"ok": True}
```

### 2.2 诊断数据结构扩展

**文件**：`backend/services/report_service.py`

当前 `_diagnose_profile` 返回的 diagnosis item 结构：
```python
{
    "source": str,              # 项目名
    "status": "pass" | "needs_improvement",
    "highlight": str,
    "issues": list[str],
    "suggestion": str,
}
```

需要新增两个字段让前端能定位到数据源：

```python
{
    # ... 原有字段
    "source_type": "resume" | "growth_log",  # 来源类型
    "source_id": int | str,                  # ProjectRecord.id 或 profile_json.projects 索引
    "current_text": str,                     # 当前描述原文，供前端编辑
}
```

修改 `_diagnose_profile()` 函数：

```python
# 在 items_to_check 构建时，同时记录 source_type 和 source_id
# Resume-extracted projects
for i, p in enumerate(raw_projects):
    if isinstance(p, str) and p.strip():
        items_to_check.append({
            "name": p[:20], "text": p,
            "source_type": "resume", "source_id": i,
        })
    elif isinstance(p, dict):
        name = p.get("name", "")
        desc = p.get("description", "") or name
        if desc:
            items_to_check.append({
                "name": name or desc[:20], "text": desc,
                "source_type": "resume", "source_id": i,
            })

# Growth log projects
for p in (projects or []):
    desc = getattr(p, "description", "") or ""
    name = getattr(p, "name", "") or ""
    text = desc if desc else name
    if text and not any(i["text"] == text for i in items_to_check):
        items_to_check.append({
            "name": name or text[:20], "text": text,
            "source_type": "growth_log", "source_id": getattr(p, "id", 0),
        })

# 在最终返回 results 时也带上这两个字段
results.append({
    "source": item["name"],
    "source_type": item["source_type"],
    "source_id": item["source_id"],
    "current_text": item["text"],
    "status": "needs_improvement",
    "highlight": s.get("highlight", ""),
    "issues": item["issues"],
    "suggestion": s.get("suggestion", ""),
})
```

### 2.3 验证

```bash
cd /c/Users/liu/Desktop/CareerPlanningAgent
python -c "from backend.services.report_service import _diagnose_profile; from backend.routers.profiles import router; print('OK')"
```

---

## 三、前端实现

### 3.1 新增 API 函数

**文件**：`frontend/src/api/growthLog.ts` 或 `frontend/src/api/profile.ts`

```typescript
export async function updateProfileProject(
  projIndex: number,
  description: string,
): Promise<{ ok: boolean }> {
  return rawFetch(`/profile/me/projects/${projIndex}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ description }),
  })
}
```

ProjectRecord 已有 `updateProject` 函数，直接复用。

### 3.2 报告页「去补充」按钮

**文件**：`frontend/src/pages/ReportPage.tsx`

在诊断卡片（需要完善的项目）末尾，添加跳转按钮：

```tsx
{item.status === 'needs_improvement' && (
  <div className="mt-3 flex justify-end">
    <button
      onClick={() => {
        // 跳转到成长档案的档案精修 tab
        navigate('/growth-log?tab=refine')
      }}
      className="text-[12px] text-blue-600 hover:text-blue-700 font-medium cursor-pointer flex items-center gap-1 transition-colors duration-200"
    >
      去补充
      <ArrowRight size={12} />
    </button>
  </div>
)}
```

需要在组件顶部 `import { useNavigate } from 'react-router-dom'` 并加 `const navigate = useNavigate()`。

### 3.3 删除「学习」Tab + 新增「档案精修」Tab

**文件**：`frontend/src/pages/GrowthLogPage.tsx`

找到现有的 FilterChips（Tab 切换），替换：
- 删除 `learning` 选项（学习笔记使用量为 0）
- 新增 `refine` 选项（档案精修）

FilterChips 文件：`frontend/src/components/growth-log/FilterChips.tsx`，需要更新类型定义：
```typescript
export type FilterKey = 'all' | 'project' | 'pursuit' | 'refine'
// 删除 'learning'
```

同步删除：
- `import { LearningNoteForm }` 及其所有使用
- `listLearningNotes` 查询
- LearningNoteForm.tsx 文件可保留不删（避免破坏其他引用）

### 3.4 新增档案精修组件

**文件（新建）**：`frontend/src/components/growth-log/RefineSection.tsx`

```tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ClipboardList, Check, AlertCircle, Sparkles } from 'lucide-react'
import { motion } from 'framer-motion'
import { fetchReportList, fetchReportDetail } from '@/api/report'
import { updateProject } from '@/api/growthLog'
import { updateProfileProject } from '@/api/profile'

interface DiagnosisItem {
  source: string
  source_type: 'resume' | 'growth_log'
  source_id: number | string
  current_text: string
  status: 'pass' | 'needs_improvement'
  highlight: string
  issues: string[]
  suggestion: string
}

export function RefineSection() {
  const queryClient = useQueryClient()
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [savingKey, setSavingKey] = useState<string | null>(null)

  // 取最新报告的 diagnosis
  const reportListQuery = useQuery({
    queryKey: ['report-list-for-refine'],
    queryFn: fetchReportList,
  })
  const latestReportId = reportListQuery.data?.[0]?.id
  const reportQuery = useQuery({
    queryKey: ['report-for-refine', latestReportId],
    queryFn: () => fetchReportDetail(latestReportId!),
    enabled: !!latestReportId,
  })

  const diagnosis = (reportQuery.data?.data?.diagnosis ?? []) as DiagnosisItem[]
  const needsFix = diagnosis.filter(d => d.status === 'needs_improvement')

  const saveMut = useMutation({
    mutationFn: async ({ item, text }: { item: DiagnosisItem; text: string }) => {
      if (item.source_type === 'growth_log') {
        await updateProject(Number(item.source_id), { description: text })
      } else {
        await updateProfileProject(Number(item.source_id), text)
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      queryClient.invalidateQueries({ queryKey: ['profile'] })
    },
  })

  const getKey = (it: DiagnosisItem) => `${it.source_type}-${it.source_id}`

  if (!latestReportId || !reportQuery.data) {
    return (
      <div className="text-center py-16 text-slate-500 text-[13px]">
        请先生成一份报告
      </div>
    )
  }

  if (needsFix.length === 0) {
    return (
      <div className="text-center py-16">
        <Check size={32} className="mx-auto mb-3 text-green-500" />
        <p className="text-[14px] text-slate-700 font-medium">档案已经很棒了</p>
        <p className="text-[12px] text-slate-500 mt-1">所有项目描述都完整</p>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <Sparkles size={15} className="text-indigo-500" />
        <p className="text-[13px] font-semibold text-slate-700">
          还有 {needsFix.length} 个项目可以更亮眼
        </p>
      </div>

      <div className="space-y-4">
        {needsFix.map((item) => {
          const key = getKey(item)
          const draft = drafts[key] ?? ''
          const isSaving = savingKey === key
          const tagColor = item.source_type === 'resume' ? 'indigo' : 'blue'

          return (
            <motion.div
              key={key}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-[20px] p-5"
              style={{
                background: 'rgba(255,255,255,0.72)',
                backdropFilter: 'blur(20px)',
                border: '1px solid rgba(217,119,6,0.18)',
                boxShadow: '0 4px 20px rgba(0,0,0,0.04)',
              }}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <ClipboardList size={14} className="text-amber-600" />
                  <span className="text-[13px] font-medium text-slate-700">{item.source}</span>
                  <span
                    className="text-[10px] px-2 py-0.5 rounded-full"
                    style={{
                      background: tagColor === 'indigo' ? 'rgba(99,102,241,0.1)' : 'rgba(37,99,235,0.1)',
                      color: tagColor === 'indigo' ? '#6366f1' : '#2563eb',
                    }}
                  >
                    {item.source_type === 'resume' ? '简历' : '成长档案'}
                  </span>
                </div>
                <span
                  className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                  style={{ background: 'rgba(217,119,6,0.1)', color: '#b45309' }}
                >
                  还差一点
                </span>
              </div>

              {item.highlight && (
                <p className="text-[12px] text-slate-600 mb-1">
                  <span className="text-green-600 font-medium">亮点：</span>
                  {item.highlight}
                </p>
              )}
              <p className="text-[12px] text-slate-600 mb-3">
                <span className="text-amber-600 font-medium">差一步：</span>
                {item.issues.join('、')}
              </p>

              <div className="mb-3">
                <p className="text-[11px] text-slate-400 mb-1">当前描述</p>
                <p className="text-[12px] text-slate-500 px-3 py-2 rounded-lg bg-slate-50 border border-slate-100 leading-relaxed">
                  {item.current_text}
                </p>
              </div>

              {item.suggestion && (
                <div className="mb-3">
                  <p className="text-[11px] text-slate-400 mb-1">参考格式</p>
                  <p className="text-[12px] text-indigo-600 px-3 py-2 rounded-lg bg-indigo-50/50 border border-indigo-100 leading-relaxed">
                    {item.suggestion}
                  </p>
                </div>
              )}

              <div className="mb-3">
                <p className="text-[11px] text-slate-400 mb-1">用你的真实数据补写</p>
                <textarea
                  value={draft}
                  onChange={e => setDrafts(d => ({ ...d, [key]: e.target.value }))}
                  rows={3}
                  placeholder="填入真实的性能数据、成果数字、你的具体贡献..."
                  className="w-full text-[12px] text-slate-700 bg-white/70 border border-slate-200 rounded-lg p-3 resize-none outline-none focus:border-blue-400 leading-relaxed transition-colors duration-200"
                />
              </div>

              <div className="flex justify-end">
                <button
                  disabled={!draft.trim() || isSaving}
                  onClick={async () => {
                    setSavingKey(key)
                    try {
                      await saveMut.mutateAsync({ item, text: draft.trim() })
                      setDrafts(d => { const n = { ...d }; delete n[key]; return n })
                    } finally {
                      setSavingKey(null)
                    }
                  }}
                  className="btn-glass flex items-center gap-1.5 px-4 py-1.5 text-[12px] font-medium text-slate-700 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                >
                  <Check size={12} />
                  {isSaving ? '保存中...' : '保存到档案'}
                </button>
              </div>
            </motion.div>
          )
        })}
      </div>

      <p className="text-center text-[11px] text-slate-400 mt-6">
        保存后再次「更新报告」，这些项目会变为"通过"状态
      </p>
    </div>
  )
}
```

### 3.5 在 GrowthLogPage 集成 RefineSection

**文件**：`frontend/src/pages/GrowthLogPage.tsx`

```tsx
import { RefineSection } from '@/components/growth-log/RefineSection'

// 在 Tab 条件渲染中：
{activeFilter === 'refine' && <RefineSection />}
```

读 URL query param 同步 tab 状态（用于从报告页跳转）：

```tsx
const [searchParams] = useSearchParams()
const urlTab = searchParams.get('tab')
useEffect(() => {
  if (urlTab === 'refine') setActiveFilter('refine')
}, [urlTab])
```

### 3.6 FilterChips 更新

**文件**：`frontend/src/components/growth-log/FilterChips.tsx`

替换学习笔记选项为档案精修：

```typescript
// 原来: { key: 'learning', label: '学习', icon: BookOpen }
// 改为: { key: 'refine', label: '档案精修', icon: Sparkles }
```

---

## 四、闭环验证

### 完整测试流程

1. 启动前后端
2. 登录 test11 账号（profile 已存在，目标岗位 系统C++工程师）
3. 访问 `/report` 生成报告，观察「档案体检」板块应有待完善项
4. 点击某待完善项的「去补充」按钮 → 跳转到 `/growth-log?tab=refine`
5. 档案精修 Tab 应自动激活，显示待完善项列表
6. 在某一项的 textarea 填入具体数据（如 "单机支撑 12000 QPS, p99 延迟 < 3ms"）
7. 点击「保存到档案」→ 后端更新对应 ProjectRecord 或 profile_json
8. 返回 `/report` 点击「更新报告」
9. 新报告的「档案体检」中，已修正的项目应显示"通过"

### 验证命令

```bash
# 后端类型/语法
cd /c/Users/liu/Desktop/CareerPlanningAgent
python -c "from backend.routers.profiles import router; print('OK')"

# 前端类型
cd /c/Users/liu/Desktop/CareerPlanningAgent/frontend
npx tsc --noEmit
```

两个命令都必须通过。

---

## 五、涉及文件清单

### 新增
- `frontend/src/components/growth-log/RefineSection.tsx`（档案精修面板）

### 修改
- `backend/routers/profiles.py`（新增 PATCH /me/projects/{index}）
- `backend/services/report_service.py`（diagnosis 增加 source_type/source_id/current_text）
- `frontend/src/api/profile.ts`（或 growthLog.ts，新增 updateProfileProject）
- `frontend/src/pages/ReportPage.tsx`（诊断卡片加「去补充」按钮）
- `frontend/src/pages/GrowthLogPage.tsx`（Tab 切换到 refine 时渲染 RefineSection，支持 URL query）
- `frontend/src/components/growth-log/FilterChips.tsx`（替换学习笔记选项）

---

## 六、不在本次范围内（后续版本）

以下功能确认**不做**：
- AI 协助重写（违背"学生自己填"原则）
- 保存后即时重新诊断（要做但放在下一版）
- Before/After 对比动画
- 完成庆祝动画
- LearningNote 相关后端清理（表可保留）

---

## 七、关键约束

- **不改变现有 API 签名**，只新增
- **不破坏现有组件**，LearningNoteForm.tsx 保留不删
- **所有新增按钮必须有 `cursor-pointer`**
- **所有过渡动画必须有 `transition-*` + duration 200ms**
- **图标必须用 Lucide，不得用 emoji**
- **文本必须是 slate-700/slate-500/slate-400 三级**
- **保持 glass card 圆角 `rounded-[20px]`**
