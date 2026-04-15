import { FolderGit2, Briefcase, Trash2 } from 'lucide-react'
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

// Type is distinguished by icon + label; neither gets its own chroma.
// Both use slate so the 3 semantic colors (blue/green/red) below stay clean.
const TYPE_CONFIG = {
  project:  { label: '项目', color: '#475569', bg: 'rgba(71,85,105,0.08)', icon: FolderGit2 },
  pursuit:  { label: '实战', color: '#475569', bg: 'rgba(71,85,105,0.08)', icon: Briefcase },
}

const STATUS_TEXT: Record<string, string> = {
  planning: '计划中', in_progress: '进行中', completed: '已完成',
  pending: '待投递', applied: '已投递', screening: '筛选中',
  scheduled: '已约面', interviewed: '已面试', debriefed: '已复盘',
  offer: 'Offer', rejected: '未通过', withdrawn: '已放弃',
}

// 3 semantic colors + slate neutral:
// blue = in-progress/neutral, green = success/terminal-good, red = failure, slate = not-started/abandoned
const STATUS_COLOR: Record<string, string> = {
  // terminal success
  completed: '#16A34A', done: '#16A34A', offer: '#16A34A',
  // in-progress (all stages blue — icon+label carry the sub-status)
  in_progress: '#2563EB', applied: '#2563EB', screening: '#2563EB',
  scheduled: '#2563EB', interviewed: '#2563EB', debriefed: '#2563EB',
  // terminal failure
  rejected: '#EF4444',
  // not-started / abandoned
  planning: '#94A3B8', pending: '#94A3B8', withdrawn: '#94A3B8',
}

function fmtRelative(iso: string) {
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000)
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

interface RecordRowProps {
  record: UnifiedRecord
  onDelete: (record: UnifiedRecord) => void
}

export function RecordRow({ record, onDelete }: RecordRowProps) {
  const cfg = TYPE_CONFIG[record.type]
  const navigate = useNavigate()

  const viewTransitionName = `record-${record.id}`

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    onDelete(record)
  }

  const goToDetail = () => {
    if (record.type === 'project') {
      navigate(`/growth-log/projects/${(record.raw as ProjectRecord).id}`)
    } else if (record.type === 'pursuit') {
      navigate(`/growth-log/pursuits/${(record.raw as JobApplication).id}`)
    }
  }

  const handleClick = () => {
    // View Transitions: morph card → detail page title. Falls back to plain navigate.
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
      className="group relative cursor-pointer pt-4 pb-5 border-t-2 border-slate-900 hover:border-blue-700 transition-colors"
      style={{ viewTransitionName } as React.CSSProperties}
    >
      {/* Kicker row: type · date · delete */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
          <cfg.icon className="w-3 h-3" style={{ color: cfg.color }} />
          <span>{cfg.label}</span>
          <span className="text-slate-300">·</span>
          <span className="tabular-nums text-slate-400">{fmtRelative(record.date)}</span>
        </div>
        <button
          onClick={handleDelete}
          className="text-slate-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all cursor-pointer"
          aria-label={`删除 ${record.title}`}
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Headline */}
      <h2 className="text-[22px] font-bold text-slate-900 leading-[1.15] tracking-tight line-clamp-2">
        {record.title}
      </h2>
      {record.subtitle && (
        <p className="mt-2 text-[13px] text-slate-500 line-clamp-2 leading-relaxed">
          {record.subtitle}
        </p>
      )}

      {/* Tags: small uppercase tracking */}
      {record.tags && record.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-[10px] font-medium uppercase tracking-[0.14em] text-slate-400">
          {record.tags.slice(0, 4).map(tag => (
            <span key={tag}>{tag}</span>
          ))}
        </div>
      )}

      {/* Status line */}
      {record.status && statusColor && (
        <div className="mt-3 flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full" style={{ background: statusColor }} />
          <span className="text-[11px] font-medium" style={{ color: statusColor }}>
            {STATUS_TEXT[record.status] || record.status}
          </span>
        </div>
      )}
    </article>
  )
}
