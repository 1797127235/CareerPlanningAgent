# Kimi 任务：项目看板 + 项目日志页改造

## 概述

在成长档案的"#项目"筛选下新增看板视图（和面试看板同模式），同时改造项目详情页，让每个项目成为一个可持续记录进展的"项目笔记本"。

**后端零改动** — 所有 API 已齐（项目 CRUD + 日志 CRUD）。

---

## Part 1：项目看板组件

### 新建文件 `frontend/src/components/growth-log-v2/ProjectKanban.tsx`

参考已有的 `InterviewKanban.tsx` 的模式，但更简单（3 列而不是 5 列）。

```tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { rawFetch } from '@/api/client'
import { Plus, X } from 'lucide-react'

const ease = [0.22, 1, 0.36, 1] as const

interface ProjectRecord {
  id: number
  name: string
  description: string
  skills_used: string[]
  status: string
  github_url: string | null
  created_at: string
}

const STAGES = [
  { key: 'planning', label: '规划中', color: 'bg-slate-400' },
  { key: 'in_progress', label: '进行中', color: 'bg-blue-400' },
  { key: 'completed', label: '已完成', color: 'bg-emerald-400' },
]

interface Props {
  projects: ProjectRecord[]
  onRefresh: () => void
}

export function ProjectKanban({ projects, onRefresh }: Props) {
  const navigate = useNavigate()
  const [showAdd, setShowAdd] = useState(false)

  const grouped = STAGES.map(stage => ({
    ...stage,
    items: projects.filter(p => p.status === stage.key),
  }))

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-[13px] text-slate-400">
          共 {projects.length} 个项目
        </p>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[13px] font-medium text-blue-600 hover:bg-blue-50 transition-all duration-200 cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5" />
          新增项目
        </button>
      </div>

      {/* Kanban */}
      {projects.length === 0 ? (
        <div className="py-16 text-center">
          <p className="text-[14px] text-slate-400 mb-3">还没有项目记录</p>
          <button
            onClick={() => setShowAdd(true)}
            className="text-[13px] font-semibold text-blue-600 hover:text-blue-700 cursor-pointer"
          >
            创建你的第一个项目
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-3">
          {grouped.map((stage) => (
            <div key={stage.key}>
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
              <div className="space-y-2 min-h-[80px]">
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
                      onClick={() => navigate(`/growth-log/projects/${item.id}`)}
                      className="w-full text-left p-3 rounded-lg border border-slate-200/60 bg-white/70 hover:bg-white hover:border-slate-300/60 hover:-translate-y-px hover:shadow-sm transition-all duration-200 cursor-pointer"
                    >
                      <p className="text-[14px] font-semibold text-slate-700 truncate">
                        {item.name}
                      </p>
                      {item.description && (
                        <p className="text-[12px] text-slate-400 truncate mt-0.5">
                          {item.description}
                        </p>
                      )}
                      {item.skills_used.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {item.skills_used.slice(0, 3).map((skill) => (
                            <span
                              key={skill}
                              className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-500"
                            >
                              {skill}
                            </span>
                          ))}
                          {item.skills_used.length > 3 && (
                            <span className="text-[10px] text-slate-400">
                              +{item.skills_used.length - 3}
                            </span>
                          )}
                        </div>
                      )}
                    </motion.button>
                  ))
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add project modal */}
      <AnimatePresence>
        {showAdd && (
          <AddProjectModal onClose={() => setShowAdd(false)} onRefresh={onRefresh} />
        )}
      </AnimatePresence>
    </div>
  )
}


/* ── Add Project Modal ── */

function AddProjectModal({
  onClose,
  onRefresh,
}: {
  onClose: () => void
  onRefresh: () => void
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [skills, setSkills] = useState('')
  const [status, setStatus] = useState('planning')

  const qc = useQueryClient()

  const createMut = useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      rawFetch('/growth-log/projects', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      onClose()
      onRefresh()
      qc.invalidateQueries({ queryKey: ['growth-projects'] })
    },
  })

  const handleSubmit = () => {
    if (!name.trim()) return
    createMut.mutate({
      name: name.trim(),
      description: description.trim(),
      skills_used: skills.split(/[,，、]/).map(s => s.trim()).filter(Boolean),
      status,
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
        <h3 className="text-[18px] font-bold text-slate-800 mb-5">新建项目</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-[12px] font-semibold text-slate-500 mb-1.5">项目名 *</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="如 Muduo 网络库"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 text-[14px] text-slate-800 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300 transition-all"
            />
          </div>
          <div>
            <label className="block text-[12px] font-semibold text-slate-500 mb-1.5">简介</label>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="一句话描述这个项目"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 text-[14px] text-slate-800 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300 transition-all"
            />
          </div>
          <div>
            <label className="block text-[12px] font-semibold text-slate-500 mb-1.5">技术栈</label>
            <input
              value={skills}
              onChange={(e) => setSkills(e.target.value)}
              placeholder="用逗号分隔，如 C++, epoll, Reactor"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 text-[14px] text-slate-800 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300 transition-all"
            />
          </div>
          <div>
            <label className="block text-[12px] font-semibold text-slate-500 mb-2">状态</label>
            <div className="flex gap-2">
              {STAGES.map((s) => (
                <button
                  key={s.key}
                  onClick={() => setStatus(s.key)}
                  className={`px-3 py-1.5 rounded-lg text-[12px] font-medium border transition-all duration-200 cursor-pointer ${
                    status === s.key
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
            disabled={!name.trim() || createMut.isPending}
            className="px-5 py-2 rounded-lg bg-blue-600 text-white text-[13px] font-bold hover:bg-blue-700 active:scale-[0.98] transition-all disabled:opacity-30 cursor-pointer"
          >
            {createMut.isPending ? '创建中...' : '创建'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}
```

---

## Part 2：GrowthLogV2Page 集成项目看板

### 2.1 添加 import

在 `GrowthLogV2Page.tsx` 顶部加：
```tsx
import { ProjectKanban } from '@/components/growth-log-v2/ProjectKanban'
```

### 2.2 添加 state

已有 `interviewView` state 的旁边，加：
```tsx
const [projectView, setProjectView] = useState<'list' | 'kanban'>('kanban')
```

### 2.3 筛选栏加视图切换

在已有的 `{filter === 'interview' && ...}` 视图切换旁边，加项目的视图切换：

```tsx
{filter === 'project' && (
  <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-0.5">
    <button
      onClick={() => setProjectView('list')}
      className={`p-1.5 rounded-md transition-all duration-200 cursor-pointer ${
        projectView === 'list' ? 'bg-white shadow-sm text-slate-700' : 'text-slate-400 hover:text-slate-600'
      }`}
    >
      <LayoutList className="w-3.5 h-3.5" />
    </button>
    <button
      onClick={() => setProjectView('kanban')}
      className={`p-1.5 rounded-md transition-all duration-200 cursor-pointer ${
        projectView === 'kanban' ? 'bg-white shadow-sm text-slate-700' : 'text-slate-400 hover:text-slate-600'
      }`}
    >
      <Kanban className="w-3.5 h-3.5" />
    </button>
  </div>
)}
```

### 2.4 条件渲染看板

在时间线渲染区域，已有的面试看板条件后面加项目看板条件。改为：

```tsx
{filter === 'interview' && interviewView === 'kanban' ? (
  <InterviewKanban ... />
) : filter === 'project' && projectView === 'kanban' ? (
  <ProjectKanban
    projects={(projectsData?.projects ?? []) as ProjectRecord[]}
    onRefresh={() => qc.invalidateQueries({ queryKey: ['growth-projects'] })}
  />
) : (
  /* 原有的时间线渲染 */
  <div> ... </div>
)}
```

需要在文件顶部加 `const qc = useQueryClient()`（如果还没有的话）。

---

## Part 3：项目详情页改造

### 文件：`frontend/src/pages/ProjectGraphPage.tsx`

### 目标

从"交替时间线"改造为"项目笔记本"——顶部是项目信息 + 内联快速记录栏，下方是按日期分组的日志时间线。

### 3.1 项目信息区

把现有的 Header 区域从简单的 "名称 + 添加按钮" 改为完整的项目信息卡：

```tsx
{/* Project info */}
<div className="mb-6">
  <button onClick={() => navigate('/growth-log')}
    className="flex items-center gap-1 text-[13px] text-slate-400 hover:text-slate-600 transition-colors cursor-pointer mb-4">
    <ArrowLeft className="w-3.5 h-3.5" /> 返回成长档案
  </button>

  <div className="flex items-start justify-between gap-4">
    <div className="flex-1 min-w-0">
      <h1 className="text-[24px] font-bold text-slate-900 tracking-tight">
        {project?.name ?? '项目'}
      </h1>
      {project?.description && (
        <p className="text-[14px] text-slate-500 mt-1">{project.description}</p>
      )}
      {project?.skills_used && project.skills_used.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {project.skills_used.map((skill: string) => (
            <span key={skill}
              className="px-2 py-0.5 rounded-md text-[12px] font-medium bg-slate-100 text-slate-600">
              {skill}
            </span>
          ))}
        </div>
      )}
      {project?.github_url && (
        <a href={project.github_url} target="_blank" rel="noreferrer"
          className="text-[12px] text-blue-500 hover:text-blue-600 mt-2 inline-block">
          {project.github_url}
        </a>
      )}
    </div>

    {/* Status selector */}
    <div className="flex gap-1.5 shrink-0">
      {(['planning', 'in_progress', 'completed'] as const).map((s) => {
        const labels: Record<string, string> = { planning: '规划中', in_progress: '进行中', completed: '已完成' }
        const active = project?.status === s
        return (
          <button
            key={s}
            onClick={() => updateProject({ status: s })}
            className={`px-2.5 py-1 rounded-lg text-[12px] font-medium border transition-all duration-200 cursor-pointer ${
              active
                ? 'border-blue-400 bg-blue-50 text-blue-700'
                : 'border-slate-200 text-slate-400 hover:border-blue-300'
            }`}
          >
            {labels[s]}
          </button>
        )
      })}
    </div>
  </div>
</div>
```

需要加一个 `updateProject` mutation：
```tsx
const updateProjectMut = useMutation({
  mutationFn: (data: Record<string, unknown>) =>
    rawFetch(`/growth-log/projects/${projectId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  onSuccess: () => {
    qc.invalidateQueries({ queryKey: ['growth-projects'] })
  },
})
const updateProject = (data: Record<string, unknown>) => updateProjectMut.mutate(data)
```

### 3.2 内联快速记录栏（替代 modal）

把"添加进展"从弹窗 modal 改为**内联输入栏**，固定在项目信息下方：

```tsx
{/* Quick log input */}
<div className="mb-8 rounded-xl border border-slate-200/60 bg-white/50 p-4">
  <textarea
    value={newLogContent}
    onChange={(e) => setNewLogContent(e.target.value)}
    placeholder="记录一条进展..."
    rows={2}
    className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-white/50 text-[14px] text-slate-700 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300 transition-all resize-none"
  />
  <div className="flex items-center justify-between mt-3">
    <div className="flex gap-1.5">
      {(Object.entries(STATUS_CFG) as [TaskStatus, typeof STATUS_CFG[TaskStatus]][]).map(([k, cfg]) => (
        <button key={k} onClick={() => setNewLogStatus(k as TaskStatus)}
          className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold border transition-all cursor-pointer ${
            newLogStatus === k
              ? 'text-white'
              : 'text-slate-400 border-slate-200 hover:border-slate-300'
          }`}
          style={newLogStatus === k ? { background: cfg.bg, borderColor: cfg.bg } : {}}>
          {cfg.label}
        </button>
      ))}
    </div>
    <button
      onClick={handleQuickAdd}
      disabled={!newLogContent.trim() || quickAddPending}
      className="px-4 py-1.5 rounded-lg bg-blue-600 text-white text-[13px] font-bold hover:bg-blue-700 active:scale-[0.98] transition-all disabled:opacity-30 cursor-pointer"
    >
      {quickAddPending ? '记录中...' : '记录'}
    </button>
  </div>
</div>
```

需要的 state 和 mutation：
```tsx
const [newLogContent, setNewLogContent] = useState('')
const [newLogStatus, setNewLogStatus] = useState<TaskStatus>('done')

const quickAddMut = useMutation({
  mutationFn: () => createProjectLog(projectId, {
    content: newLogContent.trim(),
    task_status: newLogStatus,
  }),
  onSuccess: () => {
    setNewLogContent('')
    setNewLogStatus('done')
    qc.invalidateQueries({ queryKey: ['project-logs', projectId] })
  },
})
const quickAddPending = quickAddMut.isPending
const handleQuickAdd = () => {
  if (!newLogContent.trim()) return
  quickAddMut.mutate()
}
```

### 3.3 日志时间线改造

从**左右交替时间线**改为**单列、按日期分组**的笔记列表（和成长档案主时间线风格一致）。

去掉中间的竖线（`absolute left-1/2 ... w-0.5 bg-slate-200`）和左右交替逻辑。改为：

```tsx
{/* Logs grouped by date */}
{logs.length === 0 ? (
  <div className="py-12 text-center text-[14px] text-slate-400">
    还没有进展记录，在上面写一条吧
  </div>
) : (
  <div>
    {logGroups.map((group, gIdx) => (
      <div key={group.label}>
        <div className="flex items-center gap-3 py-4">
          <div className="flex-1 h-px bg-slate-200" />
          <span className="text-[11px] font-bold text-slate-400 tracking-wider">{group.label}</span>
          <div className="flex-1 h-px bg-slate-200" />
        </div>
        <div className="space-y-3">
          {group.items.map((log, i) => {
            const st = (log.task_status ?? 'done') as TaskStatus
            const cfg = STATUS_CFG[st]
            const isEditing = editingId === log.id

            return (
              <motion.div
                key={log.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03, duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                className="group rounded-lg border border-slate-200/60 bg-white/70 p-4 hover:bg-white hover:border-slate-300/60 transition-all duration-200"
              >
                {isEditing ? (
                  <EditCard log={log} projectId={projectId} onClose={() => setEditingId(null)} />
                ) : (
                  <>
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <p className="text-[13px] text-slate-700 leading-relaxed whitespace-pre-wrap">
                          {log.content}
                        </p>
                        {log.reflection && (
                          <p className="text-[12px] text-slate-400 mt-2 leading-relaxed italic">
                            {log.reflection}
                          </p>
                        )}
                      </div>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full text-white shrink-0"
                        style={{ background: cfg.bg }}>
                        {cfg.label}
                      </span>
                    </div>
                    <div className="flex items-center justify-between mt-3">
                      <span className="text-[11px] text-slate-400">
                        {fmtTime(log.created_at)}
                      </span>
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => setEditingId(log.id)}
                          className="p-1 rounded text-slate-400 hover:text-blue-500 hover:bg-blue-50 transition-colors cursor-pointer">
                          <Pencil className="w-3 h-3" />
                        </button>
                        <button
                          onClick={() => handleDelete(log.id)}
                          className="p-1 rounded text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors cursor-pointer">
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </motion.div>
            )
          })}
        </div>
      </div>
    ))}
  </div>
)}
```

需要一个日期分组函数：
```tsx
function fmtTime(iso: string) {
  const d = new Date(iso)
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

function groupLogsByDate(logs: LogEntry[]): { label: string; items: LogEntry[] }[] {
  const now = new Date()
  const todayStr = now.toISOString().slice(0, 10)
  const yesterdayStr = new Date(now.getTime() - 86400000).toISOString().slice(0, 10)

  const groups: Record<string, LogEntry[]> = {}

  logs.forEach((log) => {
    const dateStr = log.created_at.slice(0, 10)
    let label: string
    if (dateStr === todayStr) label = '今天'
    else if (dateStr === yesterdayStr) label = '昨天'
    else label = dateStr.slice(5).replace('-', '/')

    if (!groups[label]) groups[label] = []
    groups[label].push(log)
  })

  return Object.entries(groups).map(([label, items]) => ({ label, items }))
}
```

在组件内使用：
```tsx
const logGroups = useMemo(() => groupLogsByDate(logs), [logs])
```

需要 import `useMemo`。

### 3.4 底部反思区

在日志时间线下方，加项目反思（只在 status === 'completed' 时显示，或者始终显示但标注"项目完成后填写"）：

```tsx
{/* Project reflection */}
<div className="mt-10 pt-6 border-t border-slate-200">
  <p className="text-[13px] font-semibold text-slate-500 mb-2">
    {project?.status === 'completed' ? '项目反思' : '项目反思（完成后填写）'}
  </p>
  <textarea
    value={reflectionText}
    onChange={(e) => setReflectionText(e.target.value)}
    onBlur={() => {
      if (reflectionText !== (project?.reflection || '')) {
        updateProject({ reflection: reflectionText })
      }
    }}
    placeholder="这个项目让你学到了什么？遇到的最大挑战是什么？下次会怎么做不同？"
    rows={3}
    className="w-full px-4 py-3 rounded-lg border border-slate-200 bg-white/50 text-[13px] text-slate-700 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300 transition-all resize-none leading-relaxed"
  />
</div>
```

State：
```tsx
const [reflectionText, setReflectionText] = useState(project?.reflection || '')
// 当 project 数据加载后同步
useEffect(() => {
  if (project?.reflection !== undefined) setReflectionText(project.reflection || '')
}, [project?.reflection])
```

---

## Part 4：QuickInput 删除"记录项目"按钮

### 文件：`frontend/src/components/growth-log-v2/QuickInput.tsx`

删除"记录项目"按钮和 ProjectForm modal（和面试一样，统一走看板入口）。

找到：
```tsx
<button
  onClick={() => setShowProject(true)}
  className="px-3 py-1.5 text-[12px] font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors cursor-pointer"
>
  记录项目
</button>
```
删掉。

找到 `showProject` state、`ProjectForm` import、和 showProject modal 渲染部分，全部删掉。

删除后按钮栏只剩"发送"一个按钮。

---

## 技术约束

- framer-motion（已安装）
- lucide-react（已安装）
- rawFetch / @tanstack/react-query
- Tailwind v4
- 不引入新依赖
- 后端零改动

## 禁止

- 不要左右交替时间线（太花哨，改为单列）
- 不要 bounce/elastic 动画
- 不要 gradient text
- 不要给"添加进展"继续用 modal，改为内联输入栏
- 不要改后端 API

## 验证

1. 成长档案 "#项目" 筛选下默认显示看板（3 列：规划中/进行中/已完成）
2. 看板卡片点击跳转到 `/growth-log/projects/{id}`
3. 项目详情页：顶部项目信息 + 状态切换 + 内联记录栏 + 日志时间线
4. 内联记录栏写内容 → 选状态 → 点"记录" → 日志追加到时间线
5. 日志可编辑、可删除
6. 项目完成后可写反思
7. QuickInput 不再有"记录项目"按钮
