/**
 * 项目笔记本 — 顶部项目信息 + 内联快速记录 + 按日期分组日志时间线
 */
import { useState, useMemo, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Trash2, Pencil, Check, X } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

import { listProjects, listProjectLogs, createProjectLog, deleteProjectLog } from '@/api/growthLog'
import type { ProjectRecord, ProjectLogEntry } from '@/api/growthLog'
import { rawFetch } from '@/api/client'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'

type TaskStatus = 'done' | 'in_progress' | 'blocked'

interface LogEntry extends ProjectLogEntry {
  reflection?: string
  task_status?: TaskStatus
}

const STATUS_CFG: Record<TaskStatus, { color: string; bg: string; label: string }> = {
  done:        { color: '#fff', bg: '#16A34A', label: '已完成' },
  in_progress: { color: '#fff', bg: '#2563EB', label: '进行中' },
  blocked:     { color: '#fff', bg: '#EF4444', label: '遇到问题' },
}

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

/* ── Inline Edit Card ── */
function EditCard({ log, projectId, onClose }: {
  log: LogEntry
  projectId: number
  onClose: () => void
}) {
  const [content, setContent] = useState(log.content)
  const [reflection, setReflection] = useState(log.reflection ?? '')
  const [status, setStatus] = useState<TaskStatus>(log.task_status ?? 'done')
  const qc = useQueryClient()

  const { mutate: save, isPending } = useMutation({
    mutationFn: () => rawFetch(`/growth-log/projects/${projectId}/logs/${log.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ content: content.trim(), reflection: reflection.trim() || null, task_status: status }),
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['project-logs', projectId] })
      onClose()
    },
  })

  const inputCls = "w-full px-3 py-2 text-[12px] rounded-lg outline-none bg-white/60 border transition-colors"
  const inputStyle = { borderColor: 'var(--line)' }

  return (
    <div className="space-y-2 mt-2">
      <textarea value={content} onChange={e => setContent(e.target.value)} rows={2}
        className={inputCls + ' resize-none'} style={inputStyle} />
      <div className="flex gap-1.5">
        {(Object.entries(STATUS_CFG) as [TaskStatus, typeof STATUS_CFG[TaskStatus]][]).map(([k, cfg]) => (
          <button key={k} type="button" onClick={() => setStatus(k)}
            className="px-2 py-1 rounded-lg text-[10px] font-bold cursor-pointer transition-all border"
            style={{
              background: status === k ? cfg.bg : 'transparent',
              color: status === k ? cfg.color : 'var(--ink-3)',
              borderColor: status === k ? cfg.bg : 'var(--line)',
            }}>
            {cfg.label}
          </button>
        ))}
      </div>
      <textarea value={reflection} onChange={e => setReflection(e.target.value)} rows={2}
        placeholder="心得体会..." className={inputCls + ' resize-none'} style={inputStyle} />
      <div className="flex gap-1.5">
        <button onClick={() => save()} disabled={isPending || !content.trim()}
          className="flex items-center gap-1 px-3 py-1.5 text-[11px] font-semibold text-white rounded-lg cursor-pointer disabled:opacity-50"
          style={{ background: 'var(--chestnut)' }}>
          <Check className="w-3 h-3" /> {isPending ? '保存中...' : '保存'}
        </button>
        <button onClick={onClose}
          className="flex items-center gap-1 px-3 py-1.5 text-[11px] rounded-lg cursor-pointer border transition-colors"
          style={{ color: 'var(--ink-2)', borderColor: 'var(--line)' }}>
          <X className="w-3 h-3" /> 取消
        </button>
      </div>
    </div>
  )
}

/* ── Main ── */
export default function ProjectGraphPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const projectId = Number(id)

  const [editingId, setEditingId] = useState<number | null>(null)
  const [deleting, setDeleting] = useState<number | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null)

  const [newLogContent, setNewLogContent] = useState('')
  const [newLogStatus, setNewLogStatus] = useState<TaskStatus>('done')

  const [reflectionText, setReflectionText] = useState('')

  const { data: projectsData } = useQuery({
    queryKey: ['growth-projects'], queryFn: listProjects, staleTime: 60_000,
  })
  const project: ProjectRecord | undefined = (projectsData?.projects ?? []).find(p => p.id === projectId)

  useEffect(() => {
    if (project?.reflection !== undefined) setReflectionText(project.reflection || '')
  }, [project?.reflection])

  const { data: logsData, isLoading } = useQuery({
    queryKey: ['project-logs', projectId],
    queryFn: () => listProjectLogs(projectId),
    enabled: Number.isFinite(projectId),
    staleTime: 0,
  })
  const logs: LogEntry[] = (logsData?.logs ?? []) as LogEntry[]

  const logGroups = useMemo(() => groupLogsByDate(logs), [logs])

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

  const handleDelete = (logId: number) => setConfirmDeleteId(logId)

  const doDelete = async () => {
    if (!confirmDeleteId) return
    const id = confirmDeleteId
    setConfirmDeleteId(null)
    setDeleting(id)
    try {
      await deleteProjectLog(projectId, id)
      qc.invalidateQueries({ queryKey: ['project-logs', projectId] })
    } finally { setDeleting(null) }
  }

  if (!Number.isFinite(projectId)) {
    return (
      <div className="max-w-[760px] mx-auto px-4 py-6 md:px-8 text-center" style={{ color: 'var(--ink-2)' }}>
        <p className="mb-4">无效的项目 ID</p>
        <button onClick={() => navigate('/growth-log')} className="font-medium cursor-pointer" style={{ color: 'var(--chestnut)' }}>
          返回成长档案
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-[760px] mx-auto px-4 py-6 md:px-8" style={{ color: 'var(--ink-1)' }}>
      {/* Project info */}
      <div className="mb-6">
        <button onClick={() => navigate('/growth-log')}
          className="flex items-center gap-1 text-[13px] transition-colors cursor-pointer mb-4"
          style={{ color: 'var(--ink-3)' }}>
          <ArrowLeft className="w-3.5 h-3.5" /> 返回成长档案
        </button>

        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <h1 className="text-[24px] font-bold tracking-tight" style={{ fontFamily: 'var(--font-serif)', color: 'var(--ink-1)' }}>
              {project?.name ?? '项目'}
            </h1>
            {project?.description && (
              <p className="text-[14px] mt-1" style={{ color: 'var(--ink-2)' }}>{project.description}</p>
            )}
            {project?.skills_used && project.skills_used.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-3">
                {project.skills_used.map((skill: string) => (
                  <span key={skill}
                    className="px-2 py-0.5 rounded-md text-[12px] font-medium"
                    style={{ background: 'var(--bg-card)', color: 'var(--ink-2)', border: '1px solid var(--line)' }}>
                    {skill}
                  </span>
                ))}
              </div>
            )}
            {project?.github_url && (
              <a href={project.github_url} target="_blank" rel="noreferrer"
                className="text-[12px] mt-2 inline-block" style={{ color: 'var(--chestnut)' }}>
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
                  className="px-2.5 py-1 rounded-lg text-[12px] font-medium border transition-all duration-200 cursor-pointer"
                  style={active ? {
                    borderColor: 'var(--chestnut)',
                    background: 'rgba(184,92,56,0.08)',
                    color: 'var(--chestnut)',
                  } : {
                    borderColor: 'var(--line)',
                    color: 'var(--ink-3)',
                  }}
                >
                  {labels[s]}
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Quick log input */}
      <div className="mb-8 rounded-xl p-4" style={{ background: 'var(--bg-card)', border: '1px solid var(--line)' }}>
        <textarea
          value={newLogContent}
          onChange={(e) => setNewLogContent(e.target.value)}
          placeholder="记录一条进展..."
          rows={2}
          className="w-full px-3 py-2 rounded-lg text-[14px] placeholder:text-[var(--ink-3)] focus:outline-none focus:ring-2 transition-all resize-none"
          style={{ background: 'var(--bg-paper)', color: 'var(--ink-1)', border: '1px solid var(--line)' }}
        />
        <div className="flex items-center justify-between mt-3">
          <div className="flex gap-1.5">
            {(Object.entries(STATUS_CFG) as [TaskStatus, typeof STATUS_CFG[TaskStatus]][]).map(([k, cfg]) => (
              <button key={k} onClick={() => setNewLogStatus(k as TaskStatus)}
                className="px-2.5 py-1 rounded-lg text-[11px] font-semibold border transition-all cursor-pointer"
                style={newLogStatus === k ? { background: cfg.bg, borderColor: cfg.bg, color: '#fff' } : { color: 'var(--ink-3)', borderColor: 'var(--line)' }}>
                {cfg.label}
              </button>
            ))}
          </div>
          <button
            onClick={handleQuickAdd}
            disabled={!newLogContent.trim() || quickAddPending}
            className="px-4 py-1.5 rounded-lg text-white text-[13px] font-bold transition-all disabled:opacity-30 cursor-pointer"
            style={{ background: 'var(--chestnut)' }}
          >
            {quickAddPending ? '记录中...' : '记录'}
          </button>
        </div>
      </div>

      {/* Logs grouped by date */}
      {isLoading ? (
        <div className="space-y-4">
          {[1,2,3].map(i => <div key={i} className="h-24 rounded-xl" style={{ background: 'var(--bg-card)' }} />)}
        </div>
      ) : logs.length === 0 ? (
        <div className="py-12 text-center text-[14px]" style={{ color: 'var(--ink-3)' }}>
          还没有进展记录，在上面写一条吧
        </div>
      ) : (
        <div>
          {logGroups.map((group) => (
            <div key={group.label}>
              <div className="flex items-center gap-3 py-4">
                <div className="flex-1 h-px" style={{ background: 'var(--line)' }} />
                <span className="text-[11px] font-bold tracking-wider" style={{ color: 'var(--ink-3)' }}>{group.label}</span>
                <div className="flex-1 h-px" style={{ background: 'var(--line)' }} />
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
                      className="group rounded-lg p-4 transition-all duration-200"
                      style={{ background: 'var(--bg-card)', border: '1px solid var(--line)' }}
                    >
                      {isEditing ? (
                        <EditCard log={log} projectId={projectId} onClose={() => setEditingId(null)} />
                      ) : (
                        <>
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex-1 min-w-0">
                              <p className="text-[13px] leading-relaxed whitespace-pre-wrap" style={{ color: 'var(--ink-1)' }}>
                                {log.content}
                              </p>
                              {log.reflection && (
                                <p className="text-[12px] mt-2 leading-relaxed italic" style={{ color: 'var(--ink-3)' }}>
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
                            <span className="text-[11px]" style={{ color: 'var(--ink-3)' }}>
                              {fmtTime(log.created_at)}
                            </span>
                            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                              <button
                                onClick={() => setEditingId(log.id)}
                                className="p-1 rounded transition-colors cursor-pointer"
                                style={{ color: 'var(--ink-3)' }}>
                                <Pencil className="w-3 h-3" />
                              </button>
                              <button
                                onClick={() => handleDelete(log.id)}
                                disabled={deleting === log.id}
                                className="p-1 rounded transition-colors cursor-pointer"
                                style={{ color: 'var(--ink-3)' }}>
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

      {/* Project reflection */}
      <div className="mt-10 pt-6" style={{ borderTop: '1px solid var(--line)' }}>
        <p className="text-[13px] font-semibold mb-2" style={{ color: 'var(--ink-2)' }}>
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
          className="w-full px-4 py-3 rounded-lg text-[13px] placeholder:text-[var(--ink-3)] focus:outline-none focus:ring-2 transition-all resize-none leading-relaxed"
          style={{ background: 'var(--bg-paper)', color: 'var(--ink-1)', border: '1px solid var(--line)' }}
        />
      </div>

      {/* Delete project */}
      <div className="mt-8 pt-6 flex justify-end" style={{ borderTop: '1px solid var(--line)' }}>
        <button
          onClick={() => {
            if (confirm('确定删除这个项目？所有进展记录也会一并删除，无法恢复。')) {
              rawFetch(`/growth-log/projects/${projectId}`, { method: 'DELETE' }).then(() => {
                qc.invalidateQueries({ queryKey: ['growth-projects'] })
                navigate('/growth-log')
              })
            }
          }}
          className="text-[12px] transition-colors cursor-pointer"
          style={{ color: '#EF4444' }}
        >
          删除项目
        </button>
      </div>

      <AnimatePresence>
        {confirmDeleteId && (
          <ConfirmDialog
            message="确定删除这条进展记录？"
            onConfirm={doDelete}
            onCancel={() => setConfirmDeleteId(null)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
