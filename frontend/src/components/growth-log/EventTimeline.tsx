/**
 * EventTimeline — 成长时间轴
 *
 * 按时间顺序展示所有自动和手动记录的成长事件。
 * 替换原 OverviewTab 里的事件列表。支持事件类型过滤。
 */
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  FolderGit2,
  Mic2,
  BookOpen,
  UserPlus,
  Target,
  FileSearch,
  CheckCircle2,
  Sparkles,
} from 'lucide-react'

import { getTimeline } from '@/api/growthLog'
import type { GrowthEvent, GrowthEventType } from '@/api/growthLog'

/* ── Event metadata ── */
type EventMeta = {
  Icon: typeof FolderGit2
  color: string
  bg: string
  border: string
  category: string
}

const EVENT_META: Record<GrowthEventType, EventMeta> = {
  profile_created:   { Icon: UserPlus,    color: '#0891B2', bg: '#ECFEFF', border: '#A5F3FC', category: '画像建立' },
  direction_set:     { Icon: Target,      color: '#2563EB', bg: '#EFF6FF', border: '#BFDBFE', category: '目标设定' },
  jd_diagnosis_done: { Icon: FileSearch,  color: '#7C3AED', bg: '#F5F3FF', border: '#DDD6FE', category: 'JD诊断'  },
  project_completed: { Icon: FolderGit2,  color: '#16A34A', bg: '#F0FDF4', border: '#BBF7D0', category: '项目完成' },
  interview_done:    { Icon: Mic2,        color: '#2563EB', bg: '#EFF6FF', border: '#BFDBFE', category: '面试记录' },
  skill_confirmed:   { Icon: CheckCircle2, color: '#16A34A', bg: '#F0FDF4', border: '#BBF7D0', category: '技能确认' },
  skill_added:       { Icon: Sparkles,    color: '#EA580C', bg: '#FFF7ED', border: '#FED7AA', category: '技能新增' },
  learning_completed:{ Icon: BookOpen,    color: '#7C3AED', bg: '#F5F3FF', border: '#DDD6FE', category: '学习完成' },
}

/* ── Filter options ── */
const FILTERS: { key: GrowthEventType | ''; label: string }[] = [
  { key: '',                  label: '全部'     },
  { key: 'direction_set',     label: '方向'     },
  { key: 'jd_diagnosis_done', label: '诊断'     },
  { key: 'project_completed', label: '项目'     },
  { key: 'skill_confirmed',   label: '技能确认' },
  { key: 'interview_done',    label: '面试'     },
]

function formatDate(iso: string) {
  const d = new Date(iso)
  const now = new Date()
  const days = Math.floor((now.getTime() - d.getTime()) / 86400000)
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

/* ── Group by date ── */
function groupByDate(events: GrowthEvent[]): { label: string; events: GrowthEvent[] }[] {
  const groups: Record<string, GrowthEvent[]> = {}
  events.forEach(e => {
    const date = e.created_at.split('T')[0]
    if (!groups[date]) groups[date] = []
    groups[date].push(e)
  })
  return Object.entries(groups)
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([date, evts]) => ({
      label: formatDate(date),
      events: evts,
    }))
}

/* ── Single event card ── */
function EventCard({ event }: { event: GrowthEvent }) {
  const meta = EVENT_META[event.event_type] ?? EVENT_META.skill_added
  const delta =
    event.readiness_before != null && event.readiness_after != null
      ? event.readiness_after - event.readiness_before
      : null
  const addedSkills = event.skills_delta?.added ?? []
  const confirmedSkills = event.skills_delta?.confirmed ?? []
  const allSkills = [...addedSkills, ...confirmedSkills]

  return (
    <div
      className="flex gap-3 py-3 px-3.5 rounded-[12px] transition-colors"
      style={{ background: meta.bg, border: `1px solid ${meta.border}` }}
    >
      {/* Icon */}
      <div
        className="w-8 h-8 rounded-[8px] flex items-center justify-center shrink-0 bg-white"
        style={{ border: `1px solid ${meta.border}` }}
      >
        <meta.Icon className="w-4 h-4" style={{ color: meta.color }} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 mb-0.5">
          <span
            className="text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider"
            style={{ background: 'rgba(255,255,255,0.7)', color: meta.color }}
          >
            {meta.category}
          </span>
        </div>
        <p className="text-[13px] font-semibold text-slate-800 leading-snug">
          {event.summary}
        </p>
        {allSkills.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1.5">
            {allSkills.slice(0, 5).map(s => (
              <span
                key={s}
                className="text-[10px] px-1.5 py-0.5 rounded font-medium bg-white/60 text-slate-600 border border-white/80"
              >
                {s}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Readiness delta */}
      {delta != null && delta > 0 && (
        <div className="shrink-0 text-right">
          <span className="text-[11px] font-bold tabular-nums" style={{ color: meta.color }}>
            +{delta.toFixed(1)}%
          </span>
          <p className="text-[9px] text-slate-400 mt-0.5">覆盖率</p>
        </div>
      )}
    </div>
  )
}

/* ── Empty state ── */
function EmptyTimeline() {
  return (
    <div className="py-14 flex flex-col items-center justify-center">
      <div className="w-12 h-12 rounded-2xl bg-slate-50 flex items-center justify-center mb-3">
        <Target className="w-6 h-6 text-slate-300" />
      </div>
      <p className="text-[13px] font-semibold text-slate-600 mb-1">成长旅程即将开始</p>
      <p className="text-[11px] text-slate-400 text-center max-w-xs leading-relaxed">
        上传简历、选定方向、做 JD 诊断，关键行为会自动出现在这里。
      </p>
    </div>
  )
}

/* ── Main Timeline ── */
export function EventTimeline() {
  const [filter, setFilter] = useState<GrowthEventType | ''>('')

  const { data, isLoading } = useQuery({
    queryKey: ['growth-timeline-v2', filter],
    queryFn: () => getTimeline({ event_type: filter || undefined, limit: 60 }),
    staleTime: 60_000,
    refetchOnWindowFocus: false,
    placeholderData: prev => prev,
  })
  const events: GrowthEvent[] = (data as { events: GrowthEvent[] } | undefined)?.events ?? []
  const groups = useMemo(() => groupByDate(events), [events])

  return (
    <div className="glass-static overflow-hidden">
      {/* Filter bar */}
      <div className="flex border-b border-white/40 px-3 pt-1 overflow-x-auto">
        {FILTERS.map(f => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`px-3 py-2.5 text-[11px] font-medium border-b-2 transition-colors cursor-pointer whitespace-nowrap ${
              filter === f.key
                ? 'text-blue-600 border-blue-600 font-semibold'
                : 'text-slate-400 border-transparent hover:text-slate-700'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="p-4 space-y-2">
          {[0, 1, 2].map(i => (
            <div key={i} className="h-14 bg-slate-100 rounded-[12px] animate-pulse" />
          ))}
        </div>
      ) : groups.length === 0 ? (
        <EmptyTimeline />
      ) : (
        <div className="px-4 pb-4 space-y-4">
          {groups.map(group => (
            <div key={group.label}>
              <p className="text-[10px] font-bold text-slate-300 uppercase tracking-wider pt-3 pb-2">
                {group.label}
              </p>
              <div className="space-y-2">
                {group.events.map(e => (
                  <EventCard key={e.id} event={e} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
