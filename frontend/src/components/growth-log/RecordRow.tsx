import { useState } from 'react'
import { FolderGit2, Briefcase, Trash2, ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import type { ProjectRecord } from '@/api/growthLog'
import { deleteProject } from '@/api/growthLog'
import { deleteApplication } from '@/api/applications'
import type { JobApplication } from '@/types/application'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { useQueryClient } from '@tanstack/react-query'
import { PaperCard } from '@/components/growth-log/PaperCard'

export type RecordType = 'project' | 'pursuit'

export interface UnifiedRecord {
  id: string
  type: RecordType
  title: string
  subtitle: string
  status?: string
  tags?: string[]
  date: string
  raw: ProjectRecord | JobApplication
}

const TYPE_CONFIG = {
  project:  { label: '项目', color: 'var(--moss)', bg: 'rgba(85,130,90,0.10)', icon: FolderGit2 },
  pursuit:  { label: '实战', color: 'var(--ember)', bg: 'rgba(180,110,70,0.10)', icon: Briefcase },
}

const STATUS_TEXT: Record<string, string> = {
  planning: '计划中', in_progress: '进行中', completed: '已完成',
  pending: '待投递', applied: '已投递', screening: '筛选中',
  scheduled: '已约面', interviewed: '已面试', debriefed: '已复盘',
  offer: 'Offer', rejected: '未通过', withdrawn: '已放弃',
}

const STATUS_COLOR: Record<string, string> = {
  completed: 'var(--moss)', done: 'var(--moss)', offer: 'var(--moss)',
  in_progress: 'var(--chestnut)', applied: 'var(--chestnut)', screening: 'var(--chestnut)', scheduled: 'var(--chestnut)', interviewed: 'var(--chestnut)',
  rejected: 'oklch(0.55 0.18 30)', withdrawn: 'var(--ink-3)',
  planning: 'var(--ink-3)', pending: 'var(--ink-3)', debriefed: 'var(--ember)',
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
  const [deleting, setDeleting] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const qc = useQueryClient()
  const navigate = useNavigate()

  const invalidate = () => {
    if (record.type === 'project') qc.invalidateQueries({ queryKey: ['growth-projects'] })
    else if (record.type === 'pursuit') {
      qc.invalidateQueries({ queryKey: ['pursuits-apps'] })
      qc.invalidateQueries({ queryKey: ['pursuits-interviews'] })
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
      invalidate()
    } finally { setDeleting(false) }
  }

  const handleClick = () => {
    if (record.type === 'project') {
      navigate(`/growth-log/projects/${(record.raw as ProjectRecord).id}`)
    } else if (record.type === 'pursuit') {
      navigate(`/growth-log/pursuits/${(record.raw as JobApplication).id}`)
    }
  }

  const statusColor = record.status ? (STATUS_COLOR[record.status] ?? 'var(--ink-3)') : null

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
      <PaperCard
        className="group relative cursor-pointer hover:shadow-[0_2px_4px_rgba(60,40,20,0.05),0_6px_16px_rgba(60,40,20,0.06)] transition-shadow"
      >
        <div onClick={handleClick} className="flex flex-col gap-3">
          {/* Top row: type badge + delete */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-md flex items-center justify-center shrink-0"
                style={{ background: cfg.bg }}>
                <cfg.icon className="w-3.5 h-3.5" style={{ color: cfg.color }} />
              </div>
              <span className="text-[11px] font-bold" style={{ color: cfg.color }}>{cfg.label}</span>
            </div>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="p-1.5 rounded-md text-[var(--ink-3)] hover:text-[oklch(0.55_0.18_30)] hover:bg-[oklch(0.55_0.18_30/0.06)] opacity-0 group-hover:opacity-100 transition-all cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Title */}
          <div className="flex-1">
            <p className="text-[15px] font-bold text-[var(--ink-1)] leading-snug line-clamp-2">
              {record.title}
            </p>
            {record.subtitle && (
              <p className="text-[12px] text-[var(--ink-2)] mt-1 line-clamp-2 leading-relaxed">
                {record.subtitle}
              </p>
            )}
          </div>

          {/* Tags */}
          {record.tags && record.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {record.tags.slice(0, 3).map(tag => (
                <span key={tag} className="text-[10px] px-2 py-0.5 rounded-md bg-[var(--bg-paper)] text-[var(--ink-2)] border border-[var(--line)]">
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* Bottom: status + date + arrow */}
          <div className="flex items-center justify-between pt-1 border-t border-[var(--line)]">
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
              <span className="text-[11px] text-[var(--ink-3)] tabular-nums">{fmtRelative(record.date)}</span>
              <ArrowRight className="w-3.5 h-3.5 text-[var(--line)] group-hover:text-[var(--ink-3)] transition-colors" />
            </div>
          </div>
        </div>
      </PaperCard>
    </>
  )
}
