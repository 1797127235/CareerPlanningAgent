/**
 * EventTimeline — 结构重做
 *
 * 结构改动：
 *   1. 去掉内部 filter pills（合并到 GrowthLogPage tab 层级）
 *   2. 事件卡片加具体时间
 *   3. 少于3个事件时，右侧显示引导区
 *   4. 左侧竖线 + 圆点，事件卡左色条
 *   5. 4色分组：紫诊断/绿成长/蓝目标/橙实践
 */
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  FolderGit2, Mic2, BookOpen, UserPlus, Target, Flag,
  FileSearch, CheckCircle2, Sparkles, ArrowRight,
} from 'lucide-react'

import { getTimeline } from '@/api/growthLog'
import type { GrowthEvent, GrowthEventType } from '@/api/growthLog'

/* ── Event config ── */
type EvCfg = { Icon: typeof Target; color: string; label: string }

const EV_CFG: Record<GrowthEventType, EvCfg> = {
  profile_created:    { Icon: UserPlus,     color: '#7C3AED', label: '画像建立' },
  direction_set:      { Icon: Flag,         color: '#2563EB', label: '目标设定' },
  jd_diagnosis_done:  { Icon: FileSearch,   color: '#7C3AED', label: 'JD诊断'  },
  project_completed:  { Icon: FolderGit2,   color: '#EA580C', label: '项目完成' },
  interview_done:     { Icon: Mic2,         color: '#EA580C', label: '面试记录' },
  skill_confirmed:    { Icon: CheckCircle2, color: '#16A34A', label: '技能确认' },
  skill_added:        { Icon: Sparkles,     color: '#16A34A', label: '技能新增' },
  learning_completed: { Icon: BookOpen,     color: '#16A34A', label: '学习完成' },
}

function fmtDate(iso: string) {
  const d = new Date(iso), now = new Date()
  const days = Math.floor((now.getTime() - d.getTime()) / 86400000)
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7)  return `${days}天前`
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

function fmtTime(iso: string) {
  const d = new Date(iso)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function groupByDate(events: GrowthEvent[]) {
  const g: Record<string, GrowthEvent[]> = {}
  events.forEach(e => { const k = e.created_at.split('T')[0]; (g[k] ??= []).push(e) })
  return Object.entries(g)
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([d, evts]) => ({ label: fmtDate(d), events: evts }))
}

/* ── Single event row ── */
function EventRow({ event, isLast }: { event: GrowthEvent; isLast: boolean }) {
  const cfg = EV_CFG[event.event_type] ?? EV_CFG.skill_added
  const delta = event.readiness_before != null && event.readiness_after != null
    ? event.readiness_after - event.readiness_before : null
  const skills = [...(event.skills_delta?.added ?? []), ...(event.skills_delta?.confirmed ?? [])]
  const time = fmtTime(event.created_at)

  return (
    <div className="flex">
      {/* Spine */}
      <div className="flex flex-col items-center w-7 shrink-0 pt-[14px]">
        <div className="w-[10px] h-[10px] rounded-full shrink-0 z-10"
          style={{ background: cfg.color, boxShadow: `0 0 0 3px rgba(255,255,255,0.7)` }} />
        {!isLast && <div className="w-px flex-1 mt-1 bg-slate-200/70" style={{ minHeight: 24 }} />}
      </div>

      {/* Content — no card, just inline text */}
      <div className="flex-1 pb-5 pl-3 min-w-0">
        {/* Type + time + delta */}
        <div className="flex items-center gap-1.5 mb-0.5">
          <cfg.Icon className="w-3.5 h-3.5 shrink-0" style={{ color: cfg.color }} />
          <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: cfg.color }}>
            {cfg.label}
          </span>
          <span className="text-[10px] text-slate-400">{time}</span>
          {delta != null && delta > 0 && (
            <span className="text-[11px] font-bold tabular-nums ml-auto" style={{ color: cfg.color }}>
              +{delta.toFixed(1)}%
            </span>
          )}
        </div>

        {/* Summary */}
        <p className="text-[13px] font-medium text-slate-700 leading-snug">{event.summary}</p>

        {/* Skill tags */}
        {skills.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1.5">
            {skills.slice(0, 6).map(s => (
              <span key={s} className="text-[10px] px-1.5 py-0.5 rounded bg-white/40 text-slate-500 font-medium">
                {s}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

/* ── Getting started guide (shown alongside when few events) ── */
function GettingStartedGuide() {
  const steps = [
    { label: '上传简历建画像', href: '/profile', done: true },
    { label: '诊断一份真实 JD', href: '/profile', done: false },
    { label: '记录一个项目', href: '/growth-log?tab=projects', done: false },
  ]

  return (
    <div className="glass-static rounded-xl px-5 py-5">
      <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-3">下一步</p>
      <div className="space-y-3">
        {steps.map(s => (
          <a key={s.label} href={s.href}
            className="flex items-center gap-2.5 group cursor-pointer">
            {s.done
              ? <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
              : <div className="w-4 h-4 rounded-full border-2 border-slate-300 shrink-0 group-hover:border-blue-400 transition-colors" />
            }
            <span className={`text-[12px] font-medium group-hover:text-blue-600 transition-colors ${
              s.done ? 'text-slate-400 line-through' : 'text-slate-600'
            }`}>
              {s.label}
            </span>
            {!s.done && <ArrowRight className="w-3 h-3 text-slate-300 group-hover:text-blue-400 ml-auto transition-colors" />}
          </a>
        ))}
      </div>
    </div>
  )
}

/* ── Empty ── */
function EmptyTimeline() {
  return (
    <div className="py-14 flex flex-col items-center">
      <div className="w-10 h-10 rounded-xl bg-white/30 flex items-center justify-center mb-4">
        <Target className="w-5 h-5 text-slate-300" />
      </div>
      <p className="text-[14px] font-semibold text-slate-600 mb-3">这里会记录你的每一步</p>
      <div className="space-y-1.5 mb-4">
        {['诊断一份 JD', '设定目标方向', '开始一个项目'].map(t => (
          <p key={t} className="text-[12px] text-slate-400 text-center">
            <span className="text-slate-300 mr-1.5">·</span>{t}
          </p>
        ))}
      </div>
      <p className="text-[11px] text-slate-300 italic">系统会自动记录关键行为</p>
    </div>
  )
}

/* ── Main ── */
export function EventTimeline() {
  const { data, isLoading } = useQuery({
    queryKey: ['growth-timeline-v2'],
    queryFn: () => getTimeline({ limit: 60 }),
    staleTime: 60_000,
    refetchOnWindowFocus: false,
    placeholderData: prev => prev,
  })

  const events: GrowthEvent[] = (data as { events: GrowthEvent[] } | undefined)?.events ?? []
  const groups = useMemo(() => groupByDate(events), [events])
  const fewEvents = events.length > 0 && events.length < 3

  if (isLoading) {
    return (
      <div className="pl-9 space-y-4">
        {[0, 1, 2].map(i => <div key={i} className="h-20 bg-white/20 rounded-xl animate-pulse" />)}
      </div>
    )
  }

  if (events.length === 0) return <EmptyTimeline />

  return (
    <div className={fewEvents ? 'grid grid-cols-1 md:grid-cols-[1fr_240px] gap-5' : ''}>
      {/* Timeline column */}
      <div>
        {groups.map(group => (
          <div key={group.label}>
            {/* Date header */}
            <div className="flex items-center gap-2.5 mb-2 mt-5 first:mt-0">
              <div className="w-7 flex justify-center shrink-0">
                <div className="w-2 h-2 rounded-full bg-slate-300/80" />
              </div>
              <span className="text-[12px] font-semibold text-slate-500">{group.label}</span>
              <div className="flex-1 h-px bg-slate-200/50" />
            </div>
            {/* Events */}
            {group.events.map((e, i) => (
              <EventRow key={e.id} event={e} isLast={i === group.events.length - 1} />
            ))}
          </div>
        ))}
      </div>

      {/* Guide sidebar (only when few events) */}
      {fewEvents && (
        <div className="mt-7">
          <GettingStartedGuide />
        </div>
      )}
    </div>
  )
}
