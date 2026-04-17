# Kimi 任务：成长档案面试看板视图

## 概述

在成长档案页面的"#面试"筛选下，新增看板视图——把真实面试记录按求职阶段分列展示。用户可以在列表视图和看板视图之间切换。

---

## Part 1：后端改动

### 1.1 InterviewRecord 新增 `stage` 字段

文件：`backend/db_models.py`

在 `InterviewRecord` 类中，`result` 字段后面加一行：

```python
stage: Mapped[str] = mapped_column(String(32), nullable=False, default="applied")  # applied|written_test|interviewing|offered|rejected
```

### 1.2 数据库迁移

因为这个项目用的是 SQLite + SQLAlchemy 直接建表，不用 Alembic。需要手动加列。

在 `backend/app.py` 的 `create_tables()` 或启动逻辑里（如果有），确保新列能被创建。如果项目用的是 `Base.metadata.create_all()`，新列不会自动加到已有表上。

**最简单的方式**：写一个小迁移脚本或在 `app.py` 启动时检查并加列：

```python
# 在 app.py 的启动逻辑中加
from sqlalchemy import inspect, text

def _migrate_interview_stage(engine):
    """Add stage column to interview_records if missing."""
    insp = inspect(engine)
    columns = [c['name'] for c in insp.get_columns('interview_records')]
    if 'stage' not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE interview_records ADD COLUMN stage VARCHAR(32) NOT NULL DEFAULT 'applied'"))
            conn.commit()
```

在 `create_tables()` 后调用 `_migrate_interview_stage(engine)`。

### 1.3 序列化返回 stage

文件：`backend/routers/growth_log.py`

在 `_serialize_interview` 函数的返回字典中加：
```python
"stage": i.stage,
```

### 1.4 CreateInterviewRequest 加 stage

```python
class CreateInterviewRequest(BaseModel):
    company: str
    position: str = ""
    round: str = "技术一面"
    content_summary: str
    self_rating: str = "medium"
    result: str = "pending"
    stage: str = "applied"          # ← 新增
    reflection: Optional[str] = None
    interview_at: Optional[str] = None
    application_id: Optional[int] = None
```

在 `create_interview` 函数中，创建 record 时加 `stage=req.stage`。

### 1.5 UpdateInterviewRequest 加 stage

```python
class UpdateInterviewRequest(BaseModel):
    result: Optional[str] = None
    reflection: Optional[str] = None
    self_rating: Optional[str] = None
    stage: Optional[str] = None     # ← 新增
```

在 `update_interview` 函数中加：
```python
if req.stage is not None:
    record.stage = req.stage
```

### 1.6 模拟面试接入时默认 stage

文件：`backend/routers/interview.py`

找到创建 InterviewRecord 的地方（`submit_answers` 函数中），加 `stage="interviewing"`：

```python
interview_record = InterviewRecord(
    ...
    stage="interviewing",       # ← 新增，模拟面试默认"面试中"
)
```

---

## Part 2：前端看板组件

### 2.1 新建文件 `frontend/src/components/growth-log-v2/InterviewKanban.tsx`

```tsx
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { rawFetch } from '@/api/client'
import { Plus, X, ChevronRight } from 'lucide-react'

const ease = [0.22, 1, 0.36, 1] as const

interface InterviewRecord {
  id: number
  company: string
  position: string
  round: string
  content_summary: string
  self_rating: string
  result: string
  stage: string
  reflection: string | null
  ai_analysis: Record<string, unknown> | null
  interview_at: string | null
  created_at: string
}

const STAGES = [
  { key: 'applied', label: '已投递', color: 'bg-slate-400' },
  { key: 'written_test', label: '笔试', color: 'bg-violet-400' },
  { key: 'interviewing', label: '面试中', color: 'bg-blue-400' },
  { key: 'offered', label: '已拿offer', color: 'bg-emerald-400' },
  { key: 'rejected', label: '未通过', color: 'bg-red-300' },
]

interface Props {
  interviews: InterviewRecord[]
  onRefresh: () => void
}

export function InterviewKanban({ interviews, onRefresh }: Props) {
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [showAdd, setShowAdd] = useState(false)

  // 只显示真实面试，过滤 AI 模拟
  const realInterviews = interviews.filter(i => i.company !== 'AI 模拟')

  const grouped = STAGES.map(stage => ({
    ...stage,
    items: realInterviews.filter(i => i.stage === stage.key),
  }))

  const selected = realInterviews.find(i => i.id === selectedId) || null

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-[13px] text-slate-400">
          共 {realInterviews.length} 条面试记录
        </p>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[13px] font-medium text-blue-600 hover:bg-blue-50 transition-all duration-200 cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5" />
          新增面试
        </button>
      </div>

      {/* Kanban columns */}
      {realInterviews.length === 0 ? (
        <div className="py-16 text-center">
          <p className="text-[14px] text-slate-400 mb-3">还没有面试记录</p>
          <button
            onClick={() => setShowAdd(true)}
            className="text-[13px] font-semibold text-blue-600 hover:text-blue-700 cursor-pointer"
          >
            记录你的第一场面试
          </button>
        </div>
      ) : (
        <div className="flex gap-3 overflow-x-auto pb-4">
          {grouped.map((stage) => (
            <div key={stage.key} className="min-w-[180px] flex-1">
              {/* Column header */}
              <div className="flex items-center gap-2 mb-3">
                <div className={`w-2 h-2 rounded-full ${stage.color}`} />
                <span className="text-[13px] font-semibold text-slate-700">
                  {stage.label}
                </span>
                <span className="text-[12px] text-slate-400 tabular-nums">
                  {stage.items.length}
                </span>
              </div>

              {/* Cards */}
              <div className="space-y-2 min-h-[100px]">
                {stage.items.length === 0 ? (
                  <div className="py-6 border border-dashed border-slate-200 rounded-lg text-center">
                    <span className="text-[12px] text-slate-300">暂无</span>
                  </div>
                ) : (
                  stage.items.map((item, i) => (
                    <motion.button
                      key={item.id}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.03, duration: 0.2, ease }}
                      onClick={() => setSelectedId(item.id)}
                      className="w-full text-left p-3 rounded-lg border border-slate-200/60 bg-white/70 hover:bg-white hover:border-slate-300/60 hover:-translate-y-px hover:shadow-sm transition-all duration-200 cursor-pointer"
                    >
                      <p className="text-[14px] font-semibold text-slate-700 truncate">
                        {item.company}
                      </p>
                      <p className="text-[13px] text-slate-500 truncate mt-0.5">
                        {item.position}
                      </p>
                      <div className="flex items-center justify-between mt-2">
                        <span className="text-[11px] text-slate-400">
                          {item.round}
                        </span>
                        <span className="text-[11px] text-slate-400">
                          {item.created_at?.slice(5, 10).replace('-', '/')}
                        </span>
                      </div>
                    </motion.button>
                  ))
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Detail panel (modal) */}
      <AnimatePresence>
        {selected && (
          <InterviewDetailModal
            interview={selected}
            onClose={() => setSelectedId(null)}
            onRefresh={onRefresh}
          />
        )}
      </AnimatePresence>

      {/* Add interview modal */}
      <AnimatePresence>
        {showAdd && (
          <AddInterviewModal
            onClose={() => setShowAdd(false)}
            onRefresh={onRefresh}
          />
        )}
      </AnimatePresence>
    </div>
  )
}


/* ── Detail Modal ── */

function InterviewDetailModal({
  interview,
  onClose,
  onRefresh,
}: {
  interview: InterviewRecord
  onClose: () => void
  onRefresh: () => void
}) {
  const qc = useQueryClient()

  const updateMut = useMutation({
    mutationFn: (data: { stage?: string; result?: string; self_rating?: string }) =>
      rawFetch(`/growth/interviews/${interview.id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      onRefresh()
      qc.invalidateQueries({ queryKey: ['growth-interviews'] })
    },
  })

  const deleteMut = useMutation({
    mutationFn: () =>
      rawFetch(`/growth/interviews/${interview.id}`, { method: 'DELETE' }),
    onSuccess: () => {
      onClose()
      onRefresh()
      qc.invalidateQueries({ queryKey: ['growth-interviews'] })
    },
  })

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 8 }}
        transition={{ duration: 0.2, ease }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-xl border border-slate-200 shadow-lg w-full max-w-[480px] mx-4 p-6"
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-[18px] font-bold text-slate-800">{interview.company}</h3>
            <p className="text-[14px] text-slate-500 mt-0.5">{interview.position} · {interview.round}</p>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-slate-600 cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content summary */}
        {interview.content_summary && (
          <div className="mb-4">
            <p className="text-[12px] font-semibold text-slate-400 mb-1">面试内容</p>
            <p className="text-[13px] text-slate-600 leading-relaxed">{interview.content_summary}</p>
          </div>
        )}

        {/* Reflection */}
        {interview.reflection && (
          <div className="mb-4">
            <p className="text-[12px] font-semibold text-slate-400 mb-1">反思 / AI 评语</p>
            <p className="text-[13px] text-slate-600 leading-relaxed">{interview.reflection}</p>
          </div>
        )}

        {/* Stage selector */}
        <div className="mb-4">
          <p className="text-[12px] font-semibold text-slate-400 mb-2">求职阶段</p>
          <div className="flex flex-wrap gap-2">
            {STAGES.map((s) => (
              <button
                key={s.key}
                onClick={() => updateMut.mutate({ stage: s.key })}
                className={`px-3 py-1.5 rounded-lg text-[12px] font-medium border transition-all duration-200 cursor-pointer ${
                  interview.stage === s.key
                    ? 'border-blue-400 bg-blue-50 text-blue-700'
                    : 'border-slate-200 text-slate-500 hover:border-blue-300 hover:bg-blue-50/50'
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {/* Self rating */}
        <div className="mb-6">
          <p className="text-[12px] font-semibold text-slate-400 mb-2">自评</p>
          <div className="flex gap-2">
            {[
              { key: 'good', label: '发挥好', color: 'border-emerald-400 bg-emerald-50 text-emerald-700' },
              { key: 'medium', label: '一般', color: 'border-amber-400 bg-amber-50 text-amber-700' },
              { key: 'bad', label: '发挥差', color: 'border-red-300 bg-red-50 text-red-600' },
            ].map((r) => (
              <button
                key={r.key}
                onClick={() => updateMut.mutate({ self_rating: r.key })}
                className={`px-3 py-1.5 rounded-lg text-[12px] font-medium border transition-all duration-200 cursor-pointer ${
                  interview.self_rating === r.key ? r.color : 'border-slate-200 text-slate-500 hover:border-slate-300'
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>

        {/* Date + delete */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-100">
          <span className="text-[12px] text-slate-400">
            {interview.created_at?.slice(0, 10)}
          </span>
          <button
            onClick={() => { if (confirm('确定删除这条面试记录？')) deleteMut.mutate() }}
            className="text-[12px] text-red-400 hover:text-red-600 transition-colors cursor-pointer"
          >
            删除记录
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}


/* ── Add Interview Modal ── */

function AddInterviewModal({
  onClose,
  onRefresh,
}: {
  onClose: () => void
  onRefresh: () => void
}) {
  const [company, setCompany] = useState('')
  const [position, setPosition] = useState('')
  const [round, setRound] = useState('技术一面')
  const [stage, setStage] = useState('applied')

  const qc = useQueryClient()

  const createMut = useMutation({
    mutationFn: (data: Record<string, string>) =>
      rawFetch('/growth/interviews', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      onClose()
      onRefresh()
      qc.invalidateQueries({ queryKey: ['growth-interviews'] })
    },
  })

  const handleSubmit = () => {
    if (!company.trim()) return
    createMut.mutate({
      company: company.trim(),
      position: position.trim(),
      round,
      stage,
      content_summary: '',
      self_rating: 'medium',
      result: 'pending',
    })
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 8 }}
        transition={{ duration: 0.2, ease }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-xl border border-slate-200 shadow-lg w-full max-w-[420px] mx-4 p-6"
      >
        <h3 className="text-[18px] font-bold text-slate-800 mb-5">新增面试记录</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-[12px] font-semibold text-slate-500 mb-1.5">公司名 *</label>
            <input
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="如 字节跳动"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 text-[14px] text-slate-800 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300 transition-all"
            />
          </div>
          <div>
            <label className="block text-[12px] font-semibold text-slate-500 mb-1.5">岗位</label>
            <input
              value={position}
              onChange={(e) => setPosition(e.target.value)}
              placeholder="如 后端工程师"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 text-[14px] text-slate-800 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300 transition-all"
            />
          </div>
          <div>
            <label className="block text-[12px] font-semibold text-slate-500 mb-1.5">面试轮次</label>
            <input
              value={round}
              onChange={(e) => setRound(e.target.value)}
              placeholder="如 技术一面、HR面"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 text-[14px] text-slate-800 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300 transition-all"
            />
          </div>
          <div>
            <label className="block text-[12px] font-semibold text-slate-500 mb-2">当前阶段</label>
            <div className="flex flex-wrap gap-2">
              {STAGES.map((s) => (
                <button
                  key={s.key}
                  onClick={() => setStage(s.key)}
                  className={`px-3 py-1.5 rounded-lg text-[12px] font-medium border transition-all duration-200 cursor-pointer ${
                    stage === s.key
                      ? 'border-blue-400 bg-blue-50 text-blue-700'
                      : 'border-slate-200 text-slate-500 hover:border-blue-300'
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-[13px] font-medium text-slate-500 hover:bg-slate-50 transition-all cursor-pointer"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={!company.trim() || createMut.isPending}
            className="px-5 py-2 rounded-lg bg-blue-600 text-white text-[13px] font-bold hover:bg-blue-700 active:scale-[0.98] transition-all disabled:opacity-30 cursor-pointer"
          >
            {createMut.isPending ? '保存中...' : '保存'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}
```

---

## Part 3：GrowthLogV2Page 集成

### 3.1 添加 import

在 `GrowthLogV2Page.tsx` 顶部加：
```tsx
import { InterviewKanban } from '@/components/growth-log-v2/InterviewKanban'
import { LayoutList, Kanban } from 'lucide-react'
```

### 3.2 添加 interview 数据查询

在组件内，和其他 useQuery 并列，加：
```tsx
const { data: interviewsData, refetch: refetchInterviews } = useQuery({
  queryKey: ['growth-interviews'],
  queryFn: () => rawFetch<{ interviews: InterviewRecord[] }>('/growth/interviews'),
  staleTime: 30_000,
})
```

需要在文件顶部加 `import { rawFetch } from '@/api/client'`。

定义 InterviewRecord 类型（或在组件内直接用 any，但推荐加类型）：
```tsx
interface InterviewRecordData {
  id: number
  company: string
  position: string
  round: string
  content_summary: string
  self_rating: string
  result: string
  stage: string
  reflection: string | null
  ai_analysis: Record<string, unknown> | null
  interview_at: string | null
  created_at: string
}
```

### 3.3 添加视图切换 state

```tsx
const [interviewView, setInterviewView] = useState<'list' | 'kanban'>('kanban')
```

### 3.4 修改筛选栏

在 FilterChips 后面，当 filter === 'interview' 时显示视图切换：

找到：
```tsx
<div className="flex items-center justify-between flex-wrap gap-2">
  <FilterChips value={filter} onChange={setFilter} />
</div>
```

改为：
```tsx
<div className="flex items-center justify-between flex-wrap gap-2">
  <FilterChips value={filter} onChange={setFilter} />
  {filter === 'interview' && (
    <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-0.5">
      <button
        onClick={() => setInterviewView('list')}
        className={`p-1.5 rounded-md transition-all duration-200 cursor-pointer ${
          interviewView === 'list' ? 'bg-white shadow-sm text-slate-700' : 'text-slate-400 hover:text-slate-600'
        }`}
      >
        <LayoutList className="w-3.5 h-3.5" />
      </button>
      <button
        onClick={() => setInterviewView('kanban')}
        className={`p-1.5 rounded-md transition-all duration-200 cursor-pointer ${
          interviewView === 'kanban' ? 'bg-white shadow-sm text-slate-700' : 'text-slate-400 hover:text-slate-600'
        }`}
      >
        <Kanban className="w-3.5 h-3.5" />
      </button>
    </div>
  )}
</div>
```

### 3.5 条件渲染看板 or 列表

在时间线渲染区域（`<div>` 包着 `{entriesLoading ? ...}` 的那块），改为条件渲染：

```tsx
{filter === 'interview' && interviewView === 'kanban' ? (
  <InterviewKanban
    interviews={interviewsData?.interviews ?? []}
    onRefresh={() => refetchInterviews()}
  />
) : (
  /* 原有的时间线渲染代码不变 */
  <div>
    {entriesLoading ? (
      ...原有代码...
    )}
  </div>
)}
```

---

## 技术约束

- framer-motion（已安装）
- lucide-react（已安装）— 用 `LayoutList` 和 `Kanban` 图标
- rawFetch from '@/api/client'
- @tanstack/react-query
- Tailwind v4
- 不引入拖拽库，用点击切换状态
- 不引入新 npm 依赖

## 禁止

- 不要拖拽功能（点击卡片 → modal 里改状态）
- 不要改现有时间线视图的逻辑
- 不要改 EntryCard / LegacyRecordRow 等现有组件
- 不要 bounce/elastic 动画
- 不要 gradient text

## 验证

1. 成长档案页面点"#面试"筛选，默认显示看板视图
2. 右上角可切换列表/看板
3. 看板 5 列：已投递 / 笔试 / 面试中 / 已拿offer / 未通过
4. 点"+ 新增面试"弹出表单，填写后保存，卡片出现在对应列
5. 点卡片弹出详情，可以改阶段（卡片移到新列）、改自评、删除
6. AI 模拟面试的记录不出现在看板里
7. 切回列表视图，显示正常的时间线
