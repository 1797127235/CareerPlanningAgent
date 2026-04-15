/**
 * 项目进展页 — 交替时间线（Chronology 风格）
 * 节点左右交替，点击可编辑，支持删除
 */
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Plus, Trash2, Pencil, Check, X } from 'lucide-react'
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

// Decorative cycling palette — blue+slate shades only, no rainbow
const COLORS = ['#2563EB', '#475569', '#60A5FA', '#64748B', '#3B82F6', '#94A3B8']

function fmtDate(iso: string) {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return '--'
  const yyyy = d.getFullYear()
  const mm = d.getMonth() + 1
  const dd = d.getDate()
  const hh = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${yyyy}/${mm}/${dd} ${hh}:${min}`
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

  const inputCls = "w-full px-3 py-2 text-[12px] rounded-lg outline-none bg-white/60 border border-slate-200 focus:border-blue-400 focus:bg-white transition-colors"

  return (
    <div className="space-y-2 mt-2">
      <textarea value={content} onChange={e => setContent(e.target.value)} rows={2}
        className={inputCls + ' resize-none'} />
      <div className="flex gap-1.5">
        {(Object.entries(STATUS_CFG) as [TaskStatus, typeof STATUS_CFG[TaskStatus]][]).map(([k, cfg]) => (
          <button key={k} type="button" onClick={() => setStatus(k)}
            className="px-2 py-1 rounded-lg text-[10px] font-bold cursor-pointer transition-all border"
            style={{
              background: status === k ? cfg.bg : 'transparent',
              color: status === k ? cfg.color : '#94A3B8',
              borderColor: status === k ? cfg.bg : 'rgba(0,0,0,0.08)',
            }}>
            {cfg.label}
          </button>
        ))}
      </div>
      <textarea value={reflection} onChange={e => setReflection(e.target.value)} rows={2}
        placeholder="心得体会..." className={inputCls + ' resize-none'} />
      <div className="flex gap-1.5">
        <button onClick={() => save()} disabled={isPending || !content.trim()}
          className="flex items-center gap-1 px-3 py-1.5 text-[11px] font-semibold text-white rounded-lg cursor-pointer disabled:opacity-50"
          style={{ background: '#2563EB' }}>
          <Check className="w-3 h-3" /> {isPending ? '保存中...' : '保存'}
        </button>
        <button onClick={onClose}
          className="flex items-center gap-1 px-3 py-1.5 text-[11px] text-slate-500 rounded-lg cursor-pointer border border-slate-200 hover:bg-slate-50 transition-colors">
          <X className="w-3 h-3" /> 取消
        </button>
      </div>
    </div>
  )
}

/* ── Reflection with expand/collapse ── */
const REFLECTION_LIMIT = 60

function ReflectionText({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false)
  const isLong = text.length > REFLECTION_LIMIT

  return (
    <div className="mt-1.5">
      <p className="text-[11px] text-slate-500 leading-relaxed">
        {isLong && !expanded ? text.slice(0, REFLECTION_LIMIT) + '…' : text}
      </p>
      {isLong && (
        <button
          onClick={e => { e.stopPropagation(); setExpanded(v => !v) }}
          className="text-[10px] text-blue-500 hover:text-blue-700 cursor-pointer mt-0.5 transition-colors"
        >
          {expanded ? '收起' : '展开全文'}
        </button>
      )}
    </div>
  )
}

/* ── Add Form (modal) ── */
function AddForm({ projectId, onClose }: { projectId: number; onClose: () => void }) {
  const [content, setContent] = useState('')
  const [reflection, setReflection] = useState('')
  const [status, setStatus] = useState<TaskStatus>('done')
  const qc = useQueryClient()

  const { mutate: create, isPending } = useMutation({
    mutationFn: () => createProjectLog(projectId, {
      content: content.trim(),
      reflection: reflection.trim() || undefined,
      task_status: status,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['project-logs', projectId] })
      onClose()
    },
    onError: () => {
      alert('保存失败，请重试')
    },
  })

  const inputCls = "w-full px-3.5 py-2.5 text-[13px] rounded-xl outline-none bg-slate-50 border border-slate-200 focus:border-blue-400 focus:bg-white transition-colors"

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" onClick={onClose} />
      <motion.div initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.96 }}
        className="relative bg-white rounded-2xl p-6 w-full max-w-[440px] shadow-xl z-10">
        <p className="text-[15px] font-bold text-slate-800 mb-4">添加进展</p>
        <div className="space-y-3">
          <textarea value={content} onChange={e => setContent(e.target.value)}
            placeholder="记录这条进展..." rows={2} autoFocus
            className={inputCls + ' resize-none'} />
          <div className="flex gap-2">
            {(Object.entries(STATUS_CFG) as [TaskStatus, typeof STATUS_CFG[TaskStatus]][]).map(([k, cfg]) => (
              <button key={k} type="button" onClick={() => setStatus(k)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold transition-all cursor-pointer border"
                style={{
                  background: status === k ? cfg.bg : 'transparent',
                  color: status === k ? '#fff' : '#94A3B8',
                  borderColor: status === k ? cfg.bg : 'rgba(0,0,0,0.08)',
                }}>
                {cfg.label}
              </button>
            ))}
          </div>
          <textarea value={reflection} onChange={e => setReflection(e.target.value)}
            placeholder="心得体会（可选）" rows={2}
            className={inputCls + ' resize-none'} />
          <div className="flex gap-2 pt-1">
            <button onClick={() => create()} disabled={isPending || !content.trim()}
              className="flex-1 py-2.5 text-[13px] font-semibold text-white rounded-xl cursor-pointer disabled:opacity-50 transition-colors"
              style={{ background: '#2563EB' }}>
              {isPending ? '记录中...' : '记录进展'}
            </button>
            <button onClick={onClose}
              className="px-4 py-2.5 text-[13px] text-slate-500 rounded-xl cursor-pointer border border-slate-200 hover:bg-slate-50 transition-colors">
              取消
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

/* ── Main ── */
export default function ProjectGraphPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const projectId = Number(id)

  const [showAdd, setShowAdd] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [deleting, setDeleting] = useState<number | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null)

  const { data: projectsData } = useQuery({
    queryKey: ['growth-projects'], queryFn: listProjects, staleTime: 60_000,
  })
  const project: ProjectRecord | undefined = (projectsData?.projects ?? []).find(p => p.id === projectId)

  const { data: logsData, isLoading } = useQuery({
    queryKey: ['project-logs', projectId],
    queryFn: () => listProjectLogs(projectId),
    enabled: Number.isFinite(projectId),
    staleTime: 0,
  })
  const logs: LogEntry[] = (logsData?.logs ?? []) as LogEntry[]

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
      <div className="max-w-[760px] mx-auto px-4 py-6 md:px-8 text-center">
        <p className="text-slate-500 mb-4">无效的项目 ID</p>
        <button onClick={() => navigate('/growth-log')} className="text-[var(--blue)] font-medium cursor-pointer">
          返回成长档案
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-[760px] mx-auto px-4 py-6 md:px-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <button onClick={() => navigate('/growth-log')}
          className="p-1.5 rounded-lg hover:bg-white/40 transition-colors cursor-pointer text-slate-400 hover:text-slate-700">
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="flex-1 min-w-0">
          <p
            className="text-[20px] font-bold text-slate-900 truncate"
            style={{ viewTransitionName: `record-proj-${projectId}` } as React.CSSProperties}
          >
            {project?.name ?? '项目'}
          </p>
          {project?.description && (
            <p className="text-[12px] text-slate-500 truncate mt-0.5">{project.description}</p>
          )}
        </div>
        <button onClick={() => setShowAdd(true)}
          className="flex items-center gap-1.5 px-4 py-2 bg-slate-800 text-white rounded-xl text-[12px] font-semibold hover:bg-slate-700 transition-colors cursor-pointer shrink-0">
          <Plus className="w-3.5 h-3.5" /> 添加进展
        </button>
      </div>

      {/* Timeline */}
      {isLoading ? (
        <div className="space-y-4">
          {[1,2,3].map(i => <div key={i} className="h-24 glass-static animate-pulse rounded-2xl" />)}
        </div>
      ) : logs.length === 0 ? (
        <div className="glass-static rounded-2xl py-16 text-center">
          <p className="text-[14px] text-slate-500 mb-1">还没有进展记录</p>
          <p className="text-[12px] text-slate-400">点击「添加进展」开始记录</p>
        </div>
      ) : (
        <div className="relative">
          {/* Center spine */}
          <div className="absolute left-1/2 -translate-x-1/2 top-0 bottom-0 w-0.5 bg-slate-200" />

          <div className="space-y-8">
            {logs.map((log, i) => {
              const isLeft = i % 2 === 0
              const st = (log.task_status ?? 'done') as TaskStatus
              const cfg = STATUS_CFG[st]
              const accentColor = COLORS[i % COLORS.length]
              const isEditing = editingId === log.id

              return (
                <motion.div
                  key={log.id}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.06, duration: 0.3 }}
                  className={`relative flex items-start gap-0 ${isLeft ? 'flex-row' : 'flex-row-reverse'}`}
                >
                  {/* Card */}
                  <div className={`w-[calc(50%-24px)] group flex ${isLeft ? 'pr-3 justify-end' : 'pl-3 justify-start'}`}>
                    <div
                      className="glass-static rounded-xl px-3 py-2.5 max-w-full cursor-pointer hover:shadow-md transition-shadow"
                      style={{ minWidth: 100 }}
                      onClick={() => !isEditing && setEditingId(isEditing ? null : log.id)}
                    >
                      {/* Status badge */}
                      <div className={`flex items-center gap-2 mb-1.5 ${isLeft ? 'justify-end' : 'justify-start'}`}>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full text-white"
                          style={{ background: cfg.bg }}>
                          {cfg.label}
                        </span>
                      </div>

                      {/* Content */}
                      {isEditing ? (
                        <EditCard log={log} projectId={projectId} onClose={() => setEditingId(null)} />
                      ) : (
                        <>
                          <p className="text-[13px] font-semibold text-slate-800 leading-relaxed">
                            {log.content}
                          </p>
                          {log.reflection && (
                            <ReflectionText text={log.reflection} />
                          )}
                          {/* Actions */}
                          <div className={`flex gap-1.5 mt-2 opacity-0 group-hover:opacity-100 transition-opacity ${isLeft ? 'justify-end' : 'justify-start'}`}>
                            <button
                              onClick={e => { e.stopPropagation(); setEditingId(log.id) }}
                              className="p-1 rounded text-slate-400 hover:text-blue-500 hover:bg-blue-50 transition-colors cursor-pointer">
                              <Pencil className="w-3 h-3" />
                            </button>
                            <button
                              onClick={e => { e.stopPropagation(); handleDelete(log.id) }}
                              disabled={deleting === log.id}
                              className="p-1 rounded text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors cursor-pointer">
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Center dot + date */}
                  <div className="flex flex-col items-center shrink-0 w-12 z-10">
                    <div className="w-4 h-4 rounded-full border-2 border-white shadow-sm"
                      style={{ background: accentColor }} />
                    <span className="text-[9px] text-slate-400 mt-1 tabular-nums whitespace-nowrap">
                      {fmtDate(log.created_at)}
                    </span>
                  </div>

                  {/* Empty side */}
                  <div className="w-[calc(50%-24px)]" />
                </motion.div>
              )
            })}
          </div>
        </div>
      )}

      {/* Add modal */}
      <AnimatePresence>
        {showAdd && <AddForm projectId={projectId} onClose={() => setShowAdd(false)} />}
      </AnimatePresence>

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
