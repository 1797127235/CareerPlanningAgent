import { useState, useMemo, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import Navbar from '@/components/shared/Navbar'
import { useGrowthEntries } from '@/components/growth-log/useEntries'
import type { GrowthEntry } from '@/components/growth-log/mockData'
import { ProjectForm } from '@/components/growth-log/ProjectForm'
import { InterviewForm } from '@/components/growth-log/InterviewForm'
import { listProjects } from '@/api/growthLog'
import { listApplications } from '@/api/applications'
import { rawFetch } from '@/api/client'
import type { ProjectRecord } from '@/api/growthLog'
import type { JobApplication } from '@/types/application'
import {
  BookOpen, FolderGit2, Mic, LayoutList, Kanban, Plus, Circle,
  Clock, Send, Puzzle, MessageCircle,
} from 'lucide-react'

/* ═══════════════════════════════════════════
   DESIGN TOKENS
   ═══════════════════════════════════════════ */
const serif = { fontFamily: 'var(--font-serif), Georgia, "Noto Serif SC", serif' }
const sans = { fontFamily: 'var(--font-sans), "Noto Sans SC", system-ui, sans-serif' }

const cardBase = 'rounded-2xl border border-[rgba(107,62,46,0.10)]'

/* ═══════════════════════════════════════════
   TYPES
   ═══════════════════════════════════════════ */
type FilterKey = 'all' | 'project' | 'interview' | 'learning' | 'plan'

interface InterviewRecordData {
  id: number
  company: string
  position: string
  round: string
  content_summary: string
  self_rating: string
  result: string
  stage: string
  reflection: string | null
  ai_analysis: Record<string, unknown> | null
  interview_at: string | null
  created_at: string
}

interface UnifiedRecord {
  id: string
  type: 'project' | 'pursuit'
  title: string
  subtitle: string
  status: string
  tags: string[]
  date: string
  raw: unknown
}

/* ═══════════════════════════════════════════
   HELPERS
   ═══════════════════════════════════════════ */
const FILTERS: { key: FilterKey; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'project', label: '#项目' },
  { key: 'interview', label: '#面试' },
  { key: 'learning', label: '#学习' },
  { key: 'plan', label: '计划' },
]

function fmtRelative(iso: string) {
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000)
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function fmtDate() {
  const d = new Date()
  return `${d.getFullYear()} / ${String(d.getMonth() + 1).padStart(2, '0')} / ${String(d.getDate()).padStart(2, '0')}`
}

function groupByDate<T extends { date: string }>(items: T[]) {
  const now = new Date()
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterdayStart = new Date(todayStart.getTime() - 86400000)
  const weekStart = new Date(todayStart.getTime() - todayStart.getDay() * 86400000)
  const groups: Record<string, T[]> = { 今天: [], 昨天: [], 本周: [], 更早: [] }
  items.forEach((item) => {
    const d = new Date(item.date)
    if (d >= todayStart) groups['今天'].push(item)
    else if (d >= yesterdayStart) groups['昨天'].push(item)
    else if (d >= weekStart) groups['本周'].push(item)
    else groups['更早'].push(item)
  })
  return Object.entries(groups)
    .filter(([, items]) => items.length > 0)
    .map(([label, items]) => ({ label, items }))
}

/* ═══════════════════════════════════════════
   INK WASH BACKGROUND DECORATION
   ═══════════════════════════════════════════ */
function InkWashBg() {
  return (
    <div
      className="absolute top-0 right-0 pointer-events-none"
      style={{
        width: '55%',
        height: '360px',
        zIndex: 0,
        backgroundImage: 'url(/images/ink-wash.png)',
        backgroundSize: 'cover',
        backgroundPosition: 'right top',
        opacity: 0.55,
      }}
    />
  )
}

/* ═══════════════════════════════════════════
   UI PRIMITIVES
   ═══════════════════════════════════════════ */
function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <div className={`${cardBase} ${className}`}>{children}</div>
}

/* ═══════════════════════════════════════════
   HERO SECTION
   ═══════════════════════════════════════════ */
function HeroSection() {
  const { data } = useQuery({ queryKey: ['growth-journey'], queryFn: () => rawFetch('/growth-log/journey') })
  const hasGoal = data?.has_goal && data.goal
  const label = hasGoal ? data.goal.target_label : '方向未定，也可以先开始。'
  const sub = hasGoal
    ? '阶段进度进行中，继续向目标迈进。'
    : '在学习、项目与面试之间，\n慢慢看见自己的路径。'

  return (
    <div className="relative mb-8" style={{ minHeight: 360 }}>
      <InkWashBg />
      <div className="relative" style={{ zIndex: 1 }}>
        <div className="text-[12px] text-[var(--ink-3)] tracking-widest mb-3">方向</div>
        <h1 className="text-[36px] md:text-[42px] font-black tracking-tight text-[var(--ink-1)] leading-tight mb-4" style={serif}>
          {label}
        </h1>
        <p className="text-[15px] text-[var(--ink-2)] leading-relaxed whitespace-pre-line max-w-[520px]">
          {sub}
        </p>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════
   ACTIVITY CARD
   ═══════════════════════════════════════════ */
function ActivityCard() {
  return (
    <Card className="inline-flex items-center gap-4 px-5 py-4 mb-6">
      <div className="w-10 h-10 rounded-full bg-[var(--bg-paper-2)] border border-[var(--line)] flex items-center justify-center shrink-0">
        <Clock className="w-4 h-4 text-[var(--ink-2)]" />
      </div>
      <div>
        <div className="text-[13px] font-semibold text-[var(--ink-1)] mb-0.5">最近动态</div>
        <div className="text-[12px] text-[var(--ink-3)]">最近 7 天没有新活动记录</div>
      </div>
    </Card>
  )
}

/* ═══════════════════════════════════════════
   QUICK INPUT (今日记录)
   ═══════════════════════════════════════════ */
function QuickInput({ onAdd, textareaRef }: { onAdd: (data: Partial<GrowthEntry>) => void; textareaRef: React.RefObject<HTMLTextAreaElement | null> }) {
  const [content, setContent] = useState('')
  const [tags, setTags] = useState<string[]>([])
  const [isPlan, setIsPlan] = useState(false)
  const [sending, setSending] = useState(false)

  const presetTags = ['项目', '学习']

  const toggleTag = (t: string) => {
    setTags((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]))
  }

  const handleSend = async () => {
    const text = content.trim()
    if (!text || sending) return
    setSending(true)
    try {
      await onAdd({
        content: text,
        category: 'learning',
        tags,
        structured_data: null,
        is_plan: isPlan,
        status: isPlan ? 'pending' : 'done',
        due_type: isPlan ? 'daily' : null,
        due_at: isPlan ? new Date(new Date().setHours(23, 59, 59, 999)).toISOString() : null,
        completed_at: null,
        ai_suggestions: null,
      })
      setContent('')
      setTags([])
      setIsPlan(false)
    } finally {
      setSending(false)
    }
  }

  const sendable = content.trim().length > 0 && !sending

  return (
    <Card className="mb-6 p-0 overflow-hidden">
      {/* Header */}
      <div className="px-6 pt-5 pb-3 flex items-center gap-3 border-b border-[var(--line)]/50">
        <span className="text-[14px] font-semibold text-[var(--ink-1)]" style={serif}>今日记录</span>
        <span className="text-[12px] text-[var(--ink-3)] tabular-nums">{fmtDate()}</span>
      </div>
      {/* Textarea */}
      <div className="px-6 pt-4">
        <textarea
          ref={textareaRef}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={3}
          className="w-full text-[15px] text-[var(--ink-1)] placeholder:text-[var(--ink-3)] outline-none resize-none bg-transparent leading-relaxed"
          placeholder="写下今天推进的一小步，记录学习、项目进展，或一次面试后的思考……"
          style={sans}
        />
      </div>
      {/* Footer */}
      <div className="px-6 pb-5 pt-2 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          {presetTags.map((t) => (
            <button
              key={t}
              onClick={() => toggleTag(t)}
              className={`px-3 py-1 rounded-full text-[12px] font-medium border transition-all cursor-pointer ${
                tags.includes(t)
                  ? 'border-[#6B3E2E]/30 bg-[#6B3E2E]/8 text-[#6B3E2E]'
                  : 'border-[var(--line)] text-[var(--ink-2)] hover:border-[var(--ink-2)]'
              }`}
            >
              #{t}
            </button>
          ))}
          <button
            onClick={() => {
              const name = prompt('自定义标签')
              if (name) setTags((prev) => [...prev.filter((t) => presetTags.includes(t)), name])
            }}
            className="flex items-center gap-1 px-3 py-1 rounded-full text-[12px] font-medium border border-[var(--line)] text-[var(--ink-2)] hover:border-[var(--ink-2)] transition-all cursor-pointer"
          >
            <Plus className="w-3 h-3" /> 自定义
          </button>
          <label className="flex items-center gap-1.5 text-[12px] text-[var(--ink-2)] cursor-pointer select-none ml-1">
            <input type="checkbox" checked={isPlan} onChange={(e) => setIsPlan(e.target.checked)} className="cursor-pointer" />
            标记为计划
          </label>
        </div>
        <button
          onClick={handleSend}
          disabled={!sendable}
          className={`flex items-center gap-1.5 px-5 py-2 rounded-xl text-[13px] font-medium transition-all cursor-pointer ${
            sendable
              ? 'bg-[#6B3E2E] text-white hover:bg-[#5A3426] shadow-sm'
              : 'bg-[var(--bg-paper-2)] text-[var(--ink-3)]'
          }`}
        >
          <Send className="w-3.5 h-3.5" /> {sending ? '发送中…' : '发送'}
        </button>
      </div>
    </Card>
  )
}

/* ═══════════════════════════════════════════
   FILTER CHIPS
   ═══════════════════════════════════════════ */
function FilterChips({ value, onChange }: { value: FilterKey; onChange: (v: FilterKey) => void }) {
  return (
    <div className="flex items-center gap-2 mb-6">
      {FILTERS.map((f) => {
        const active = value === f.key
        return (
          <button
            key={f.key}
            onClick={() => onChange(f.key)}
            className={`px-4 py-1.5 rounded-full text-[13px] font-medium transition-all cursor-pointer ${
              active
                ? 'bg-[#6B3E2E] text-white shadow-sm'
                : 'bg-[#F2EDE4] border border-[rgba(107,62,46,0.10)] text-[var(--ink-2)] hover:text-[var(--ink-1)] hover:border-[rgba(107,62,46,0.18)]'
            }`}
          >
            {f.label}
          </button>
        )
      })}
    </div>
  )
}

/* ═══════════════════════════════════════════
   ENTRY CARD
   ═══════════════════════════════════════════ */
function EntryCard({ entry, onDelete }: { entry: GrowthEntry; onDelete?: (id: number) => void }) {
  const categoryColor =
    entry.category === 'learning' ? '#5A7D5A'
    : entry.category === 'interview' ? '#B85C38'
    : entry.category === 'project' ? '#4A6FA5'
    : '#6B3E2E'

  return (
    <Card className="group relative hover:border-[#6B3E2E]/20 transition-colors">
      {onDelete && (
        <button
          onClick={() => onDelete(entry.id)}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-[var(--ink-3)] opacity-0 group-hover:opacity-100 hover:text-red-500 hover:bg-red-50 transition-all cursor-pointer z-10"
        >
          删除
        </button>
      )}
      <div className="flex items-start gap-3">
        <div className="w-2.5 h-2.5 rounded-full mt-2 shrink-0" style={{ background: categoryColor }} />
        <div className="flex-1 min-w-0">
          <p className="text-[15px] text-[var(--ink-1)] leading-relaxed whitespace-pre-wrap pr-12">{entry.content}</p>
          <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1">
            {entry.tags.map((t) => (
              <span key={t} className="text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--ink-3)]">#{t}</span>
            ))}
          </div>
          <div className="mt-3 flex items-center justify-between">
            <span className="text-[11px] text-[var(--ink-3)] tabular-nums">{fmtRelative(entry.created_at)}</span>
            <button className="flex items-center gap-1 text-[11px] font-medium text-[var(--ink-3)] hover:text-[#6B3E2E] transition-colors cursor-pointer">
              AI 建议
            </button>
          </div>
        </div>
      </div>
    </Card>
  )
}

/* ═══════════════════════════════════════════
   PLAN ROW
   ═══════════════════════════════════════════ */
function PlanRow({ entry, onToggle, onDrop }: { entry: GrowthEntry; onToggle: (id: number) => void; onDrop: (id: number) => void }) {
  return (
    <div className="flex items-center gap-3 py-3 border-b border-[var(--line)]/40 last:border-0">
      <button onClick={() => onToggle(entry.id)} className="shrink-0 cursor-pointer">
        <Circle className="w-4 h-4 text-[var(--line)] hover:text-[#5A7D5A] transition-colors" />
      </button>
      <div className="flex-1 min-w-0">
        <p className="text-[13px] text-[var(--ink-1)]">{entry.content}</p>
        <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1">
          {entry.tags.map((t) => (
            <span key={t} className="text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--ink-3)]">#{t}</span>
          ))}
        </div>
      </div>
      <button onClick={() => onDrop(entry.id)} className="shrink-0 text-[11px] text-[var(--ink-3)] hover:text-red-500 transition-colors cursor-pointer">
        放弃
      </button>
    </div>
  )
}

/* ═══════════════════════════════════════════
   EMPTY STATE
   ═══════════════════════════════════════════ */
function EmptyState({ onFocus }: { onFocus: () => void }) {
  const cards = [
    { icon: BookOpen, title: '学习', desc: '理解如何发生', action: onFocus },
    { icon: Puzzle, title: '项目', desc: '能力如何成形' },
    { icon: MessageCircle, title: '面试', desc: '经验如何回响' },
  ]

  return (
    <Card className="p-8">
      <div className="text-center mb-6">
        <p className="text-[14px] text-[var(--ink-2)]">还没有任何记录 —— 从第一笔开始</p>
      </div>
      <div className="grid grid-cols-3 gap-4">
        {cards.map((c) => (
          <button
            key={c.title}
            onClick={c.action}
            className={`${cardBase} p-6 text-center hover:border-[#6B3E2E]/20 transition-colors cursor-pointer`}
          >
            <div className="w-12 h-12 rounded-full bg-[var(--bg-paper-2)] border border-[var(--line)] flex items-center justify-center mx-auto mb-3">
              <c.icon className="w-5 h-5 text-[var(--ink-2)]" />
            </div>
            <h3 className="text-[15px] font-semibold text-[var(--ink-1)] mb-1" style={serif}>{c.title}</h3>
            <p className="text-[12px] text-[var(--ink-3)]">{c.desc}</p>
          </button>
        ))}
      </div>
    </Card>
  )
}

/* ═══════════════════════════════════════════
   PROJECT KANBAN
   ═══════════════════════════════════════════ */
function ProjectKanban({ projects, onRefresh, onAddEntry }: { projects: ProjectRecord[]; onRefresh: () => void; onAddEntry: (data: Partial<GrowthEntry>) => Promise<unknown> | unknown }) {
  const [showAdd, setShowAdd] = useState(false)
  const stages = [
    { key: 'planning', label: '规划中', color: 'bg-[var(--ink-3)]' },
    { key: 'in_progress', label: '进行中', color: 'bg-[#B8860B]' },
    { key: 'completed', label: '已完成', color: 'bg-[#5A7D5A]' },
  ]

  const grouped = stages.map((s) => ({ ...s, items: projects.filter((p) => p.status === s.key) }))

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-[13px] text-[var(--ink-3)]">共 {projects.length} 个项目</p>
        <button onClick={() => setShowAdd(true)} className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[13px] font-medium bg-[var(--bg-paper-2)] border border-[var(--line)] text-[var(--ink-2)] hover:text-[var(--ink-1)] hover:border-[var(--ink-2)] transition-all cursor-pointer">
          <Plus className="w-3.5 h-3.5" /> 新增项目
        </button>
      </div>
      <div className="grid grid-cols-3 gap-3">
        {grouped.map((stage) => (
          <div key={stage.key}>
            <div className="flex items-center gap-2 mb-3">
              <div className={`w-2 h-2 rounded-full ${stage.color}`} />
              <span className="text-[13px] font-semibold text-[var(--ink-1)]">{stage.label}</span>
              <span className="text-[12px] text-[var(--ink-3)] tabular-nums">{stage.items.length}</span>
            </div>
            <div className="space-y-2 min-h-[80px]">
              {stage.items.length === 0 ? (
                <div className="py-6 border border-dashed border-[var(--line)] rounded-xl text-center">
                  <span className="text-[12px] text-[var(--ink-3)]">暂无</span>
                </div>
              ) : (
                stage.items.map((p) => (
                  <div key={p.id} className={`${cardBase} p-3 hover:border-[#6B3E2E]/20 transition-colors cursor-pointer group relative`}>
                    <button
                      onClick={async (e) => {
                        e.stopPropagation()
                        if (!confirm('确定删除这个项目？')) return
                        await rawFetch(`/growth-log/projects/${p.id}`, { method: 'DELETE' })
                        onRefresh()
                      }}
                      className="absolute top-2 right-2 p-1.5 rounded-md text-[var(--ink-3)] opacity-0 group-hover:opacity-100 hover:text-red-500 transition-all cursor-pointer z-10"
                    >
                      删除
                    </button>
                    <p className="text-[14px] font-semibold text-[var(--ink-1)] truncate pr-6">{p.name}</p>
                    {p.description && <p className="text-[12px] text-[var(--ink-3)] truncate mt-0.5">{p.description}</p>}
                    {p.skills_used.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {p.skills_used.slice(0, 3).map((s) => (
                          <span key={s} className="px-2 py-0.5 text-[10px] font-medium rounded-full bg-[var(--bg-paper-2)] text-[var(--ink-2)]">{s}</span>
                        ))}
                        {p.skills_used.length > 3 && <span className="text-[10px] text-[var(--ink-3)]">+{p.skills_used.length - 3}</span>}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        ))}
      </div>

      {showAdd && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6" style={{ background: 'rgba(60,50,40,0.18)' }} onClick={() => setShowAdd(false)}>
          <div
            className="w-full max-w-[460px] rounded-[24px] p-8 md:p-10"
            style={{
              background: '#F5F0E8',
              border: '1px solid rgba(107,62,46,0.10)',
              boxShadow: '0 24px 64px rgba(60,50,40,0.12), 0 2px 8px rgba(60,50,40,0.06)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-[22px] font-bold tracking-tight mb-1.5" style={{ fontFamily: 'var(--font-serif)', color: '#2A2118' }}>新建项目</h2>
            <p className="text-[13px] mb-8" style={{ color: '#9A8B7A' }}>记录一个新项目，追踪它的进展</p>
            <ProjectForm
              onClose={() => setShowAdd(false)}
              onSaved={() => { onRefresh(); }}
              onAddEntry={onAddEntry}
            />
          </div>
        </div>
      )}
    </div>
  )
}

/* ═══════════════════════════════════════════
   INTERVIEW KANBAN
   ═══════════════════════════════════════════ */
function InterviewKanban({ interviews, onRefresh, onAddEntry }: { interviews: InterviewRecordData[]; onRefresh: () => void; onAddEntry: (data: Partial<GrowthEntry>) => Promise<unknown> | unknown }) {
  const [showAdd, setShowAdd] = useState(false)
  const stages = [
    { key: 'applied', label: '已投递', color: 'bg-[var(--ink-3)]' },
    { key: 'written_test', label: '笔试', color: 'bg-violet-400' },
    { key: 'interviewing', label: '面试中', color: 'bg-[#4A6FA5]' },
    { key: 'offered', label: '已拿offer', color: 'bg-[#5A7D5A]' },
    { key: 'rejected', label: '未通过', color: 'bg-red-300' },
  ]

  const realInterviews = interviews.filter((i) => i.company !== 'AI 模拟')
  const grouped = stages.map((s) => ({ ...s, items: realInterviews.filter((i) => i.stage === s.key) }))

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-[13px] text-[var(--ink-3)]">共 {realInterviews.length} 条面试记录</p>
        <button onClick={() => setShowAdd(true)} className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[13px] font-medium bg-[var(--bg-paper-2)] border border-[var(--line)] text-[var(--ink-2)] hover:text-[var(--ink-1)] hover:border-[var(--ink-2)] transition-all cursor-pointer">
          <Plus className="w-3.5 h-3.5" /> 新增面试
        </button>
      </div>
      <div className="grid grid-cols-5 gap-3">
        {grouped.map((stage) => (
          <div key={stage.key}>
            <div className="flex items-center gap-2 mb-3">
              <div className={`w-2 h-2 rounded-full ${stage.color}`} />
              <span className="text-[13px] font-semibold text-[var(--ink-1)]">{stage.label}</span>
              <span className="text-[12px] text-[var(--ink-3)] tabular-nums">{stage.items.length}</span>
            </div>
            <div className="space-y-2 min-h-[100px]">
              {stage.items.length === 0 ? (
                <div className="py-6 border border-dashed border-[var(--line)] rounded-xl text-center">
                  <span className="text-[12px] text-[var(--ink-3)]">暂无</span>
                </div>
              ) : (
                stage.items.map((item) => (
                  <div key={item.id} className={`${cardBase} p-3 hover:border-[#6B3E2E]/20 transition-colors cursor-pointer`}>
                    <p className="text-[14px] font-semibold text-[var(--ink-1)] truncate">{item.company}</p>
                    <p className="text-[13px] text-[var(--ink-2)] truncate mt-0.5">{item.position}</p>
                    <div className="flex items-center justify-between mt-2">
                      <span className="text-[11px] text-[var(--ink-3)]">{item.round}</span>
                      <span className="text-[11px] text-[var(--ink-3)]">{item.created_at?.slice(5, 10).replace('-', '/')}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        ))}
      </div>

      {showAdd && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6" style={{ background: 'rgba(60,50,40,0.18)' }} onClick={() => setShowAdd(false)}>
          <div
            className="w-full max-w-[520px] rounded-[24px] p-8 md:p-10"
            style={{
              background: '#F5F0E8',
              border: '1px solid rgba(107,62,46,0.10)',
              boxShadow: '0 24px 64px rgba(60,50,40,0.12), 0 2px 8px rgba(60,50,40,0.06)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <InterviewForm
              onClose={() => setShowAdd(false)}
              onSaved={() => { onRefresh(); }}
              onAddEntry={onAddEntry}
            />
          </div>
        </div>
      )}
    </div>
  )
}

/* ═══════════════════════════════════════════
   MAIN PAGE
   ═══════════════════════════════════════════ */
export default function GrowthLogPage() {
  const { entries, loading: entriesLoading, addEntry, updateEntry, deleteEntry } = useGrowthEntries()
  const [filter, setFilter] = useState<FilterKey>('all')
  const [interviewView, setInterviewView] = useState<'list' | 'kanban'>('kanban')
  const [projectView, setProjectView] = useState<'list' | 'kanban'>('kanban')
  const qc = useQueryClient()
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const { data: projectsData } = useQuery({ queryKey: ['growth-projects'], queryFn: listProjects, staleTime: 120_000 })
  const { data: appsData } = useQuery<JobApplication[]>({ queryKey: ['pursuits-apps'], queryFn: listApplications, staleTime: 120_000 })
  const { data: interviewsData, refetch: refetchInterviews } = useQuery({
    queryKey: ['growth-interviews'],
    queryFn: () => rawFetch<{ interviews: InterviewRecordData[] }>('/growth-log/interviews'),
    staleTime: 30_000,
  })

  const focusInput = () => {
    textareaRef.current?.focus()
    textareaRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  const plans = entries.filter((e) => e.is_plan && e.status === 'pending')

  const legacyRecords = useMemo<UnifiedRecord[]>(() => {
    const projects = projectsData?.projects ?? []
    const applications = appsData ?? []
    return [
      ...projects.map((p) => ({ id: `proj-${p.id}`, type: 'project' as const, title: p.name, subtitle: p.description || '', status: p.status, tags: p.skills_used, date: p.created_at, raw: p })),
      ...applications.map((a) => ({ id: `app-${a.id}`, type: 'pursuit' as const, title: `${a.company || '未知公司'} · ${a.position || a.jd_title || '未命名岗位'}`, subtitle: '', status: a.status, tags: [], date: a.created_at, raw: a })),
    ].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
  }, [projectsData, appsData])

  const timelineItems = useMemo(() => {
    const newItems = entries.filter((e) => !e.is_plan || e.status !== 'pending').map((e) => ({ kind: 'entry' as const, entry: e, date: e.created_at }))
    const oldItems = legacyRecords.map((r) => ({ kind: 'legacy' as const, record: r, date: r.date }))
    const all = [...newItems, ...oldItems].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
    if (filter === 'all') return all
    if (filter === 'project') return all.filter((i) => (i.kind === 'entry' && i.entry.category === 'project') || (i.kind === 'legacy' && i.record.type === 'project'))
    if (filter === 'interview') return all.filter((i) => i.kind === 'entry' && i.entry.category === 'interview')
    if (filter === 'learning') return all.filter((i) => i.kind === 'entry' && i.entry.category === 'learning')
    return []
  }, [entries, legacyRecords, filter])

  const groups = useMemo(() => groupByDate(timelineItems), [timelineItems])

  const handleTogglePlan = async (id: number) => {
    await updateEntry(id, { status: 'done', completed_at: new Date().toISOString() })
  }
  const handleDropPlan = async (id: number) => {
    await updateEntry(id, { status: 'dropped' })
  }

  return (
    <div className="min-h-screen bg-[var(--bg-paper)] text-[var(--ink-1)]">
      <Navbar />
      <main className="pt-[80px] pb-20">
        <div className="mx-auto w-full max-w-[1440px] px-6 md:px-12">
          {/* Hero */}
          <HeroSection />

          {/* Activity */}
          <ActivityCard />

          {/* Quick Input */}
          <QuickInput onAdd={addEntry} textareaRef={textareaRef} />

          {/* Filters + View Toggle */}
          <div className="flex items-center justify-between flex-wrap gap-2">
            <FilterChips value={filter} onChange={setFilter} />
            {filter === 'interview' && (
              <div className="flex items-center gap-1 bg-[#F2EDE4] border border-[rgba(107,62,46,0.10)] rounded-lg p-0.5">
                <button onClick={() => setInterviewView('list')} className={`p-1.5 rounded-md transition-all cursor-pointer ${interviewView === 'list' ? 'bg-[var(--bg-paper-2)] shadow-sm text-[var(--ink-1)]' : 'text-[var(--ink-3)] hover:text-[var(--ink-1)]'}`}><LayoutList className="w-3.5 h-3.5" /></button>
                <button onClick={() => setInterviewView('kanban')} className={`p-1.5 rounded-md transition-all cursor-pointer ${interviewView === 'kanban' ? 'bg-[var(--bg-paper-2)] shadow-sm text-[var(--ink-1)]' : 'text-[var(--ink-3)] hover:text-[var(--ink-1)]'}`}><Kanban className="w-3.5 h-3.5" /></button>
              </div>
            )}
            {filter === 'project' && (
              <div className="flex items-center gap-1 bg-[#F2EDE4] border border-[rgba(107,62,46,0.10)] rounded-lg p-0.5">
                <button onClick={() => setProjectView('list')} className={`p-1.5 rounded-md transition-all cursor-pointer ${projectView === 'list' ? 'bg-[var(--bg-paper-2)] shadow-sm text-[var(--ink-1)]' : 'text-[var(--ink-3)] hover:text-[var(--ink-1)]'}`}><LayoutList className="w-3.5 h-3.5" /></button>
                <button onClick={() => setProjectView('kanban')} className={`p-1.5 rounded-md transition-all cursor-pointer ${projectView === 'kanban' ? 'bg-[var(--bg-paper-2)] shadow-sm text-[var(--ink-1)]' : 'text-[var(--ink-3)] hover:text-[var(--ink-1)]'}`}><Kanban className="w-3.5 h-3.5" /></button>
              </div>
            )}
          </div>

          {/* Plans */}
          {filter !== 'plan' && plans.length > 0 && (
            <section className="mb-8">
              <div className="flex items-center gap-4 pt-2 pb-4">
                <div className="flex-1 h-px bg-[var(--line)]" />
                <span className="text-[11px] font-bold text-[var(--ink-3)] tracking-[0.2em]">待完成的计划</span>
                <div className="flex-1 h-px bg-[var(--line)]" />
              </div>
              <Card className="px-4">
                {plans.map((plan) => (
                  <PlanRow key={plan.id} entry={plan} onToggle={handleTogglePlan} onDrop={handleDropPlan} />
                ))}
              </Card>
            </section>
          )}

          {/* Content */}
          {filter === 'interview' && interviewView === 'kanban' ? (
            <InterviewKanban interviews={interviewsData?.interviews ?? []} onRefresh={() => refetchInterviews()} onAddEntry={addEntry} />
          ) : filter === 'project' && projectView === 'kanban' ? (
            <ProjectKanban projects={projectsData?.projects ?? []} onRefresh={() => qc.invalidateQueries({ queryKey: ['growth-projects'] })} onAddEntry={addEntry} />
          ) : (
            <div>
              {entriesLoading ? (
                <div className="pt-12 text-[var(--ink-3)] text-[13px] text-center">加载中…</div>
              ) : groups.length === 0 ? (
                <EmptyState onFocus={focusInput} />
              ) : (
                groups.map((group) => (
                  <div key={group.label}>
                    <div className="flex items-center gap-4 pt-8 pb-5">
                      <div className="flex-1 h-px bg-[var(--line)]" />
                      <span className="text-[11px] font-bold text-[var(--ink-3)] tracking-[0.2em]">{group.label}</span>
                      <div className="flex-1 h-px bg-[var(--line)]" />
                    </div>
                    <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
                      {group.items.map((item, i) => (
                        <div key={item.kind === 'entry' ? `entry-${item.entry.id}-${i}` : `legacy-${item.record.id}-${i}`}>
                          {item.kind === 'entry' ? (
                            <EntryCard entry={item.entry} onDelete={deleteEntry} />
                          ) : (
                            <Card className="hover:border-[#6B3E2E]/20 transition-colors cursor-pointer">
                              <p className="text-[14px] font-semibold text-[var(--ink-1)]">{item.record.title}</p>
                              <p className="text-[12px] text-[var(--ink-3)] mt-1">{fmtRelative(item.record.date)}</p>
                            </Card>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
