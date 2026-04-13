import { useState } from 'react'
import { FolderGit2, Briefcase, BookOpen, Trash2, ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import type { ProjectRecord, LearningNote } from '@/api/growthLog'
import { deleteProject, deleteLearningNote } from '@/api/growthLog'
import { deleteApplication } from '@/api/applications'
import type { JobApplication } from '@/types/application'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { useQueryClient } from '@tanstack/react-query'

export type RecordType = 'project' | 'pursuit' | 'learning'

export interface UnifiedRecord {
  id: string
  type: RecordType
  title: string
  subtitle: string
  status?: string
  tags?: string[]
  date: string
  raw: ProjectRecord | JobApplication | LearningNote
}

const TYPE_CONFIG = {
  project:  { label: '项目', color: '#EA580C', bg: 'rgba(234,88,12,0.10)', icon: FolderGit2 },
  pursuit:  { label: '实战', color: '#2563EB', bg: 'rgba(37,99,235,0.10)',  icon: Briefcase },
  learning: { label: '学习', color: '#16A34A', bg: 'rgba(22,163,74,0.10)',  icon: BookOpen },
}

const STATUS_TEXT: Record<string, string> = {
  planning: '计划中', in_progress: '进行中', completed: '已完成',
  pending: '待投递', applied: '已投递', screening: '筛选中',
  scheduled: '已约面', interviewed: '已面试', debriefed: '已复盘',
  offer: 'Offer', rejected: '未通过', withdrawn: '已放弃',
}

const STATUS_COLOR: Record<string, string> = {
  completed: '#16A34A', done: '#16A34A', offer: '#16A34A',
  in_progress: '#2563EB', applied: '#2563EB', screening: '#2563EB', scheduled: '#2563EB', interviewed: '#2563EB',
  rejected: '#EF4444', withdrawn: '#94A3B8',
  planning: '#94A3B8', pending: '#94A3B8', debriefed: '#0891B2',
}

function fmtRelative(iso: string) {
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000)
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

export function RecordRow({ record }: { record: UnifiedRecord }) {
  const cfg = TYPE_CONFIG[record.type]
  const [detailOpen, setDetailOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const qc = useQueryClient()
  const navigate = useNavigate()

  const invalidate = () => {
    if (record.type === 'project') qc.invalidateQueries({ queryKey: ['growth-projects'] })
    else if (record.type === 'pursuit') {
      qc.invalidateQueries({ queryKey: ['pursuits-apps'] })
      qc.invalidateQueries({ queryKey: ['pursuits-interviews'] })
    } else {
      qc.invalidateQueries({ queryKey: ['learning-notes'] })
    }
  }

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    setShowConfirm(true)
  }

  const doDelete = async () => {
    setShowConfirm(false)
    setDeleting(true)
    try {
      if (record.type === 'project') await deleteProject((record.raw as ProjectRecord).id)
      else if (record.type === 'pursuit') await deleteApplication((record.raw as JobApplication).id)
      else await deleteLearningNote((record.raw as LearningNote).id)
      invalidate()
    } finally { setDeleting(false) }
  }

  const handleClick = () => {
    if (record.type === 'project') {
      navigate(`/growth-log/projects/${(record.raw as ProjectRecord).id}`)
    } else if (record.type === 'pursuit') {
      navigate(`/growth-log/pursuits/${(record.raw as JobApplication).id}`)
    } else {
      setDetailOpen(true)
    }
  }

  const statusColor = record.status ? (STATUS_COLOR[record.status] ?? '#94A3B8') : null

  return (
    <>
      <AnimatePresence>
        {showConfirm && (
          <ConfirmDialog
            message={`确定删除「${record.title}」吗？`}
            onConfirm={doDelete}
            onCancel={() => setShowConfirm(false)}
          />
        )}
      </AnimatePresence>
      <div
        onClick={handleClick}
        className="glass group relative cursor-pointer p-5 flex flex-col gap-3"
      >
        {/* Top row: type badge + delete */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
              style={{ background: cfg.bg }}>
              <cfg.icon className="w-3.5 h-3.5" style={{ color: cfg.color }} />
            </div>
            <span className="text-[11px] font-bold" style={{ color: cfg.color }}>{cfg.label}</span>
          </div>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="p-1.5 rounded-lg text-slate-300 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all cursor-pointer"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Title */}
        <div className="flex-1">
          <p className="text-[15px] font-bold text-slate-900 leading-snug line-clamp-2">
            {record.title}
          </p>
          {record.subtitle && (
            <p className="text-[12px] text-slate-500 mt-1 line-clamp-2 leading-relaxed">
              {record.subtitle}
            </p>
          )}
        </div>

        {/* Tags */}
        {record.tags && record.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {record.tags.slice(0, 3).map(tag => (
              <span key={tag} className="text-[10px] px-2 py-0.5 rounded-md bg-white/60 text-slate-500 border border-white/60">
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* Bottom: status + date + arrow */}
        <div className="flex items-center justify-between pt-1 border-t border-white/40">
          <div className="flex items-center gap-1.5">
            {record.status && statusColor && (
              <>
                <div className="w-1.5 h-1.5 rounded-full" style={{ background: statusColor }} />
                <span className="text-[11px] font-medium" style={{ color: statusColor }}>
                  {STATUS_TEXT[record.status] || record.status}
                </span>
              </>
            )}
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] text-slate-400 tabular-nums">{fmtRelative(record.date)}</span>
            <ArrowRight className="w-3.5 h-3.5 text-slate-300 group-hover:text-slate-500 transition-colors" />
          </div>
        </div>
      </div>

      {detailOpen && record.type === 'learning' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={() => setDetailOpen(false)}>
          <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" />
          <div className="relative bg-white rounded-2xl p-6 w-full max-w-[480px] shadow-xl z-10" onClick={e => e.stopPropagation()}>
            <p className="text-[15px] font-bold text-slate-800 mb-3">{record.title}</p>
            <p className="text-[13px] text-slate-600 leading-relaxed whitespace-pre-wrap">
              {record.subtitle || '暂无摘要'}
            </p>
            {(record.raw as LearningNote).tags?.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-4">
                {(record.raw as LearningNote).tags.map(t => (
                  <span key={t} className="text-[11px] px-2.5 py-1 bg-green-50 text-green-600 rounded-lg">#{t}</span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}
