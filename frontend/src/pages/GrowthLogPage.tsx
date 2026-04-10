/**
 * 成长档案页 — Tab 式管理中心
 * 总览 | 项目 | 实战经历
 * 实战经历：紧凑列表 + 点击弹出详情 modal
 */
import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, FolderGit2, Mic2, BookOpen } from 'lucide-react'

import { getTimeline, getMonthlySummary } from '@/api/growthLog'
import type { GrowthEvent, MonthlySummary } from '@/api/growthLog'
import { fetchProfile } from '@/api/profiles'
import type { CareerGoal } from '@/types/profile'
import { ProjectsSection } from '@/components/growth-log/ProjectsSection'
import { PursuitsSection } from '@/components/growth-log/PursuitsSection'

/* ═══ Constants ═══ */
type TabKey = 'overview' | 'projects' | 'pursuits'

const TABS: { key: TabKey; label: string }[] = [
  { key: 'overview', label: '总览' },
  { key: 'projects', label: '项目' },
  { key: 'pursuits', label: '实战经历' },
]

const FILTERS: { key: string; label: string }[] = [
  { key: '', label: '全部' },
  { key: 'project_completed', label: '项目' },
  { key: 'interview_done', label: '面试' },
  { key: 'learning_completed', label: '学习' },
]

const EVENT_ICON: Record<string, { Icon: typeof FolderGit2; color: string; bg: string; border: string }> = {
  project_completed:  { Icon: FolderGit2, color: '#16A34A', bg: '#F0FDF4', border: '#BBF7D0' },
  interview_done:     { Icon: Mic2,       color: '#2563EB', bg: '#EFF6FF', border: '#BFDBFE' },
  learning_completed: { Icon: BookOpen,   color: '#7C3AED', bg: '#F5F3FF', border: '#DDD6FE' },
  skill_added:        { Icon: BookOpen,   color: '#EA580C', bg: '#FFF7ED', border: '#FED7AA' },
}


function timeAgo(iso: string) {
  const d = new Date(iso)
  const now = new Date()
  const days = Math.floor((now.getTime() - d.getTime()) / 86400000)
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

/* ═══════════════════════════════════════════════════════════════
   总览 Tab
   ═══════════════════════════════════════════════════════════════ */

/* ── Overview helpers ── */

function composeSentence(summary: MonthlySummary | undefined, goal: CareerGoal | undefined): string {
  if (!summary) return ''
  const acts: string[] = []
  if (summary.projects > 0) acts.push(`${summary.projects} 个项目`)
  if (summary.interviews > 0) acts.push(`${summary.interviews} 场面试`)
  if (summary.learnings > 0) acts.push(`${summary.learnings} 次学习`)

  if (acts.length === 0) {
    return goal
      ? `还没有本月记录，去做第一个 ${goal.target_label ? '面向' + goal.target_label + '的' : ''}项目或练习吧。`
      : '记录你的项目和面试，开始追踪成长进度。'
  }

  const target = goal?.target_label ? `冲 ${goal.target_label}` : '冲目标岗位'
  const total = summary.total_events ?? (summary.projects + summary.interviews + summary.learnings)
  const encouragement = total >= 5 ? '势头不错' : total >= 2 ? '持续积累' : '开了个好头'
  return `本月完成了${acts.join('、')}，${encouragement}，继续${target}。`
}

function groupEventsByDate(events: GrowthEvent[]): { label: string; events: GrowthEvent[] }[] {
  const groups: Record<string, GrowthEvent[]> = {}
  events.forEach(e => {
    const date = e.created_at.split('T')[0]
    if (!groups[date]) groups[date] = []
    groups[date].push(e)
  })
  return Object.entries(groups)
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([date, evts]) => {
      const d = new Date(date)
      const days = Math.floor((Date.now() - d.getTime()) / 86400000)
      const label = days === 0 ? '今天' : days === 1 ? '昨天' : days < 7 ? `${days}天前` : `${d.getMonth() + 1}月${d.getDate()}日`
      return { label, events: evts }
    })
}

const MAJOR_EVENTS = new Set(['project_completed', 'interview_done'])

function OverviewTab({ summary, summaryLoading }: { summary?: MonthlySummary; summaryLoading: boolean }) {
  const [filter, setFilter] = useState('')

  const { data: profile } = useQuery({
    queryKey: ['profile-overview'],
    queryFn: fetchProfile,
    staleTime: 5 * 60_000,
  })
  const goal = profile?.career_goals?.find((g: CareerGoal) => g.is_primary)
    ?? profile?.career_goals?.[0]

  const { data } = useQuery({
    queryKey: ['growth-timeline', filter],
    queryFn: () => getTimeline({ event_type: filter || undefined, limit: 60 }),
    staleTime: 3 * 60_000, gcTime: 10 * 60_000, refetchOnWindowFocus: false,
    placeholderData: (prev: unknown) => prev,
  })
  const events: GrowthEvent[] = (data as { events: GrowthEvent[] } | undefined)?.events ?? []
  const groups = groupEventsByDate(events)
  const sentence = composeSentence(summary, goal)

  return (
    <div className="space-y-4">

      {/* ── Head: Status card ── */}
      <div className="glass rounded-[18px] p-5"
        style={{ background: 'linear-gradient(135deg, rgba(37,99,235,0.06), rgba(124,58,237,0.04))' }}>
        {summaryLoading ? (
          <div className="h-5 w-2/3 rounded bg-white/40 animate-pulse" />
        ) : goal ? (
          <>
            <p className="text-[13px] leading-relaxed text-[#1a1a1a] font-medium">{sentence}</p>
            <div className="flex items-center gap-2 mt-3 flex-wrap">
              <span className="text-[10px] font-semibold px-2.5 py-1 rounded-[6px]"
                style={{ background: 'rgba(37,99,235,0.10)', color: '#2563EB' }}>
                目标：{goal.target_label}
              </span>
              {(summary?.total_events ?? 0) > 0 && (
                <span className="text-[10px] text-[#8E8E93]">
                  本月 <span className="font-bold text-[#1a1a1a]">{summary!.total_events}</span> 条记录
                </span>
              )}
              {(summary?.readiness_delta ?? 0) > 0 && (
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-[5px]"
                  style={{ background: 'rgba(22,163,74,0.08)', color: '#16A34A' }}>
                  ↑{summary!.readiness_delta!.toFixed(1)}% 准备度
                </span>
              )}
            </div>
          </>
        ) : (
          <div className="flex items-center justify-between">
            <p className="text-[12px] text-[#8E8E93]">设定目标岗位，解锁个性化成长分析</p>
            <a href="/profile" className="text-[11px] font-semibold px-3 py-1.5 rounded-[8px] cursor-pointer"
              style={{ background: '#2563EB', color: '#fff' }}>
              去设定
            </a>
          </div>
        )}
      </div>

      {/* ── Middle: Activity rings ── */}
      {(() => {
        const CIRC = 2 * Math.PI * 30
        const TARGET = 5  // full ring = 5 activities/month
        const items = [
          { label: '本月项目', value: summary?.projects   ?? 0, unit: '个', color: '#16A34A', bg: 'rgba(22,163,74,0.06)',   border: 'rgba(22,163,74,0.14)'   },
          { label: '本月面试', value: summary?.interviews  ?? 0, unit: '场', color: '#2563EB', bg: 'rgba(37,99,235,0.06)',   border: 'rgba(37,99,235,0.14)'   },
          { label: '本月学习', value: summary?.learnings   ?? 0, unit: '次', color: '#7C3AED', bg: 'rgba(124,58,237,0.06)',  border: 'rgba(124,58,237,0.14)'  },
        ]
        return (
          <div className="grid grid-cols-3 gap-3">
            {items.map(item => {
              const pct = summaryLoading ? 0 : Math.min(item.value / TARGET, 1)
              const offset = CIRC * (1 - pct)
              return (
                <div key={item.label}
                  className="flex flex-col items-center gap-2 py-4 rounded-[18px]"
                  style={{ background: item.bg, border: `1px solid ${item.border}` }}>
                  {/* Ring */}
                  <div className="relative" style={{ width: 72, height: 72 }}>
                    <svg width="72" height="72" viewBox="0 0 72 72"
                      style={{ transform: 'rotate(-90deg)' }}>
                      <circle cx="36" cy="36" r="30" fill="none"
                        stroke="rgba(0,0,0,0.07)" strokeWidth="5" />
                      <circle cx="36" cy="36" r="30" fill="none"
                        stroke={item.color} strokeWidth="5" strokeLinecap="round"
                        strokeDasharray={CIRC}
                        strokeDashoffset={item.value > 0 ? offset : CIRC}
                        style={{ transition: 'stroke-dashoffset 0.8s cubic-bezier(0.23,1,0.32,1)' }}
                      />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span style={{ fontSize: 22, fontWeight: 900, color: item.color, lineHeight: 1 }}>
                        {summaryLoading ? '—' : item.value}
                      </span>
                      <span style={{ fontSize: 9, color: '#9CA3AF', marginTop: 2 }}>{item.unit}</span>
                    </div>
                  </div>
                  <p style={{ fontSize: 11, fontWeight: 700, color: '#374151' }}>{item.label}</p>
                </div>
              )
            })}
          </div>
        )
      })()}

      {/* ── Bottom: Timeline grouped by date ── */}
      <div className="glass rounded-[16px] overflow-hidden">
        {/* Filter tabs */}
        <div className="flex border-b border-[#F2F2F7] px-4 pt-1">
          {FILTERS.map(f => (
            <button key={f.key} onClick={() => setFilter(f.key)}
              className={`px-3 py-2.5 text-[11px] font-medium border-b-2 transition-all cursor-pointer ${
                filter === f.key
                  ? 'text-[var(--blue)] border-[var(--blue)] font-semibold'
                  : 'text-[#8E8E93] border-transparent hover:text-[#1a1a1a]'
              }`}>
              {f.label}
            </button>
          ))}
        </div>

        {groups.length === 0 ? (
          <div className="py-12 text-center">
            <p className="text-[12px] text-[#8E8E93]">暂无记录，去添加项目或面试吧</p>
          </div>
        ) : (
          <div className="px-4 pb-4 space-y-4">
            {groups.map(group => (
              <div key={group.label}>
                {/* Date label */}
                <p className="text-[10px] font-bold text-[#C7C7CC] uppercase tracking-wider pt-3 pb-1.5">
                  {group.label}
                </p>
                <div className="space-y-1">
                  {group.events.map(e => {
                    const meta = EVENT_ICON[e.event_type] ?? EVENT_ICON.skill_added
                    const delta = e.readiness_before != null && e.readiness_after != null
                      ? e.readiness_after - e.readiness_before : null
                    const isMajor = MAJOR_EVENTS.has(e.event_type)

                    return isMajor ? (
                      /* Major event — project / interview */
                      <div key={e.id} className="flex gap-3 py-2.5 px-3 rounded-[12px]"
                        style={{ background: meta.bg, border: `1px solid ${meta.border}` }}>
                        <div className="w-8 h-8 rounded-[8px] flex items-center justify-center shrink-0"
                          style={{ background: '#fff', border: `1px solid ${meta.border}` }}>
                          <meta.Icon className="w-4 h-4" style={{ color: meta.color }} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-[13px] font-semibold text-[#1a1a1a] leading-snug">{e.summary}</p>
                          {(e.skills_delta?.added ?? []).length > 0 && (
                            <div className="flex gap-1 mt-1 flex-wrap">
                              {e.skills_delta!.added!.slice(0, 4).map(s => (
                                <span key={s} className="text-[9px] px-1.5 py-0.5 rounded font-medium"
                                  style={{ background: 'rgba(255,255,255,0.7)', color: meta.color }}>{s}</span>
                              ))}
                            </div>
                          )}
                        </div>
                        {delta != null && delta > 0 && (
                          <span className="text-[10px] font-bold shrink-0 self-start"
                            style={{ color: meta.color }}>+{delta.toFixed(1)}%</span>
                        )}
                      </div>
                    ) : (
                      /* Minor event — learning / skill */
                      <div key={e.id} className="flex gap-2.5 py-1.5 px-2">
                        <div className="w-5 h-5 rounded-[5px] flex items-center justify-center shrink-0 mt-0.5"
                          style={{ background: meta.bg }}>
                          <meta.Icon className="w-2.5 h-2.5" style={{ color: meta.color }} />
                        </div>
                        <p className="text-[11px] text-[#636366] flex-1 leading-snug">{e.summary}</p>
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════
   Main Page
   ═══════════════════════════════════════════════════════════════ */

export default function GrowthLogPage() {
  const qc = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get('tab') as TabKey | null
  const [activeTab, setActiveTab] = useState<TabKey>(tabParam && TABS.some(t => t.key === tabParam) ? tabParam : 'overview')

  useEffect(() => {
    if (activeTab !== 'overview') setSearchParams({ tab: activeTab }, { replace: true })
    else setSearchParams({}, { replace: true })
  }, [activeTab, setSearchParams])

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['growth-summary'], queryFn: getMonthlySummary, staleTime: 3 * 60_000, retry: 1,
  })

  // Dropdown state
  const [menuOpen, setMenuOpen] = useState(false)
  useEffect(() => {
    if (!menuOpen) return
    const close = () => setMenuOpen(false)
    document.addEventListener('click', close)
    return () => document.removeEventListener('click', close)
  }, [menuOpen])

  return (
    <div className="max-w-[820px] mx-auto px-4 py-5 md:px-8" style={{ background: 'transparent' }}>
      {/* Tab bar + add button */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex gap-1">
          {TABS.map(t => (
            <button key={t.key} onClick={() => setActiveTab(t.key)}
              className={`px-3.5 py-2 rounded-lg text-[12px] font-medium transition-all cursor-pointer ${
                activeTab === t.key ? 'bg-[var(--blue)] text-white shadow-sm' : 'text-[#8E8E93] hover:text-[#1a1a1a] hover:bg-white/50'
              }`}>
              {t.label}
            </button>
          ))}
        </div>

        <div className="relative">
          <button onClick={e => { e.stopPropagation(); setMenuOpen(!menuOpen) }}
            className="flex items-center gap-1 px-3 py-2 bg-[var(--blue)] text-white text-[11px] font-semibold rounded-lg hover:opacity-90 cursor-pointer">
            <Plus className="w-3.5 h-3.5" /> 记录
          </button>
          <AnimatePresence>
            {menuOpen && (
              <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.1 }}
                className="absolute right-0 top-full mt-1 w-36 bg-white rounded-xl shadow-lg border border-[#F2F2F7] overflow-hidden z-30"
                onClick={e => e.stopPropagation()}>
                <button onClick={() => { setActiveTab('pursuits'); setMenuOpen(false) }}
                  className="w-full flex items-center gap-2 px-3.5 py-2.5 text-[11px] text-[#1a1a1a] hover:bg-[#F5F5F7] cursor-pointer font-medium">
                  <Mic2 className="w-3.5 h-3.5 text-[#2563EB]" /> 岗位追踪
                </button>
                <button onClick={() => { setActiveTab('projects'); setMenuOpen(false) }}
                  className="w-full flex items-center gap-2 px-3.5 py-2.5 text-[11px] text-[#1a1a1a] hover:bg-[#F5F5F7] border-t border-[#F2F2F7] cursor-pointer font-medium">
                  <FolderGit2 className="w-3.5 h-3.5 text-[#16A34A]" /> 记录项目
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {activeTab === 'overview' && <OverviewTab summary={summary} summaryLoading={summaryLoading} />}
      {activeTab === 'projects' && <ProjectsSection />}
      {activeTab === 'pursuits' && <PursuitsSection />}
    </div>
  )
}
