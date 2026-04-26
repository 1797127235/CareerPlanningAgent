import { FolderGit2, Briefcase } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { ProjectRecord } from '@/api/growthLog'
import type { JobApplication } from '@/types/application'

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
  project: { label: '项目', color: 'var(--text-2)', icon: FolderGit2 },
  pursuit: { label: '实战', color: 'var(--text-2)', icon: Briefcase },
}

const STATUS_TEXT: Record<string, string> = {
  planning: '计划中',
  in_progress: '进行中',
  completed: '已完成',
  pending: '待投递',
  applied: '已投递',
  screening: '筛选中',
  scheduled: '已约面',
  interviewed: '已面试',
  debriefed: '已复盘',
  offer: 'Offer',
  rejected: '未通过',
  withdrawn: '已放弃',
}

const STATUS_COLOR: Record<string, string> = {
  completed: '#22c55e',
  done: '#22c55e',
  offer: '#22c55e',
  in_progress: 'var(--blue)',
  applied: 'var(--blue)',
  screening: 'var(--blue)',
  scheduled: 'var(--blue)',
  interviewed: 'var(--blue)',
  debriefed: 'var(--blue)',
  rejected: '#ef4444',
  planning: 'var(--text-3)',
  pending: 'var(--text-3)',
  withdrawn: 'var(--text-3)',
}

function fmtRelative(iso: string) {
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000)
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

interface LegacyRecordRowProps {
  record: UnifiedRecord
}

export function LegacyRecordRow({ record }: LegacyRecordRowProps) {
  const cfg = TYPE_CONFIG[record.type]
  const navigate = useNavigate()

  const viewTransitionName = `record-${record.id}`

  const goToDetail = () => {
    if (record.type === 'project') {
      navigate(`/growth-log/projects/${(record.raw as ProjectRecord).id}`)
    } else if (record.type === 'pursuit') {
      navigate(`/growth-log/pursuits/${(record.raw as JobApplication).id}`)
    }
  }

  const handleClick = () => {
    const doc = typeof document !== 'undefined' ? document : null
    const startVT = (doc as unknown as { startViewTransition?: (cb: () => void) => void })?.startViewTransition
    if (startVT) {
      startVT.call(doc, goToDetail)
    } else {
      goToDetail()
    }
  }

  const statusColor = record.status ? (STATUS_COLOR[record.status] ?? '#94A3B8') : null

  return (
    <article
      onClick={handleClick}
      className="group relative cursor-pointer glass p-4"
      style={{ viewTransitionName } as React.CSSProperties}
    >
      <div className="g-inner">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--text-3)]">
            <cfg.icon className="w-3 h-3" style={{ color: cfg.color }} />
            <span>{cfg.label}</span>
            <span className="text-[var(--text-3)]/40">·</span>
            <span className="tabular-nums text-[var(--text-3)]">{fmtRelative(record.date)}</span>
          </div>
        </div>

        <h2 className="text-[22px] font-bold text-[var(--text-1)] leading-[1.15] tracking-tight line-clamp-2">
          {record.title}
        </h2>
        {record.subtitle && (
          <p className="mt-2 text-[13px] text-[var(--text-2)] line-clamp-2 leading-relaxed">{record.subtitle}</p>
        )}

        {record.tags && record.tags.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--text-3)]">
            {record.tags.slice(0, 4).map((tag) => (
              <span key={tag}>{tag}</span>
            ))}
          </div>
        )}

        {record.status && statusColor && (
          <div className="mt-3 flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full" style={{ background: statusColor }} />
            <span className="text-[11px] font-medium" style={{ color: statusColor }}>
              {STATUS_TEXT[record.status] || record.status}
            </span>
          </div>
        )}
      </div>
    </article>
  )
}
