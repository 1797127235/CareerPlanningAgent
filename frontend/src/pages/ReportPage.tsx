/**
 * ReportPage — 职业生涯发展报告
 * Fetches real data from /api/report/. Falls back to generation prompt if no report exists.
 */
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  Area, AreaChart, XAxis, YAxis, Tooltip,
} from 'recharts'
import {
  Sparkles, Download, Edit3, Check, Zap, BookOpen,
  Briefcase, ArrowUpRight, AlertCircle, RefreshCw, TrendingUp, BarChart2,
  Target, FolderGit2, ClipboardList, Trash2,
} from 'lucide-react'
import {
  fetchReportList, fetchReportDetail, generateReport,
  editReport, polishReport, deleteReport,
  fetchPlan, updatePlanCheck,
} from '@/api/report'
import type { PlanStage } from '@/api/report'

// ── Types ─────────────────────────────────────────────────────────────────────

interface FourDim {
  foundation: number | null
  skills: number
  qualities: number | null
  potential: number
}

interface SkillGapTier {
  total: number
  matched: number
  pct: number
  practiced_count: number  // verified in projects
  claimed_count: number    // resume-only
}

interface MissingSkill {
  name: string
  freq: number   // 0.0–1.0 JD frequency
  tier: 'core' | 'important' | 'bonus'
}

interface MatchedSkill {
  name: string
  tier: 'core' | 'important' | 'bonus'
  status: 'completed' | 'practiced' | 'claimed'
  freq: number
}

interface SkillGap {
  core: SkillGapTier
  important: SkillGapTier
  bonus: SkillGapTier
  top_missing: MissingSkill[]
  matched_skills: MatchedSkill[]
  has_project_data: boolean
  positioning: string
  positioning_level: 'junior' | 'mid' | 'senior'
}

interface ActionItem {
  id: string
  type: 'skill' | 'project' | 'job_prep'
  sub_type?: 'validate' | 'learn'
  text: string
  tag: string
  skill_name?: string
  priority: 'high' | 'medium'
  done: boolean
  phase?: number
  deliverable?: string
}

interface ActionPlan {
  stages?: PlanStage[]
  skills: ActionItem[]
  project: ActionItem[]
  job_prep: ActionItem[]
}

interface ReportData {
  match_score: number
  four_dim: FourDim
  narrative: string
  market: {
    demand_change_pct: number | null
    salary_cagr: number | null
    salary_p50: number
    timing: 'best' | 'good' | 'caution' | 'wait'
    timing_label: string
  }
  skill_gap?: SkillGap
  growth_curve: { date: string; score: number }[]
  action_plan: ActionPlan
  target: { node_id: string; label: string; zone: string }
  delta?: {
    prev_score: number
    score_change: number
    prev_date: string
    gained_skills: string[]
    still_missing: string[]
    plan_progress: { done: number; total: number } | null
    next_action: string | null
  } | null
  promotion_path?: { level: number; title: string }[]
  soft_skills?: Record<string, number>
  positioning?: string
  positioning_level?: 'junior' | 'mid' | 'senior'
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function ScoreRing({ score, size = 136 }: { score: number; size?: number }) {
  const r = size * 0.4
  const circ = 2 * Math.PI * r
  const offset = circ * (1 - score / 100)
  const color = score >= 75 ? '#16a34a' : score >= 50 ? '#2563eb' : '#f59e0b'
  const center = size / 2
  const fontSize = size >= 120 ? 'text-3xl' : 'text-xl'

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={center} cy={center} r={r} fill="none" stroke="rgba(255,255,255,0.35)" strokeWidth={size >= 120 ? 10 : 7} />
        <circle
          cx={center} cy={center} r={r} fill="none"
          stroke={color} strokeWidth={size >= 120 ? 10 : 7} strokeLinecap="round"
          strokeDasharray={circ} strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 1.2s ease' }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className={`${fontSize} font-bold text-slate-800 tabular-nums`}>{score}</span>
        <span className="text-[11px] text-slate-500 font-medium">匹配分</span>
      </div>
    </div>
  )
}

function DimBadge({ label, value }: { label: string; value: number | null }) {
  if (value === null) {
    return (
      <div className="flex flex-col items-center gap-1">
        <div className="flex items-center gap-1 text-slate-400">
          <AlertCircle size={12} />
          <span className="text-[11px]">暂无数据</span>
        </div>
        <span className="text-[11px] font-semibold text-slate-400">{label}</span>
      </div>
    )
  }
  const color = value >= 75 ? '#16a34a' : value >= 50 ? '#2563eb' : '#f59e0b'
  return (
    <div className="flex flex-col items-center gap-1">
      <span className="text-xl font-bold tabular-nums" style={{ color }}>{value}</span>
      <span className="text-[11px] font-semibold text-slate-500">{label}</span>
    </div>
  )
}

function TimingBadge({ timing, label }: { timing: string; label: string }) {
  const map: Record<string, { bg: string; text: string; border: string }> = {
    best:    { bg: 'rgba(22,163,74,0.12)',   text: '#15803d', border: 'rgba(22,163,74,0.25)' },
    good:    { bg: 'rgba(37,99,235,0.10)',   text: '#1d4ed8', border: 'rgba(37,99,235,0.25)' },
    caution: { bg: 'rgba(234,179,8,0.12)',   text: '#a16207', border: 'rgba(234,179,8,0.30)' },
    wait:    { bg: 'rgba(239,68,68,0.10)',   text: '#b91c1c', border: 'rgba(239,68,68,0.25)' },
  }
  const s = map[timing] ?? map.good
  return (
    <span
      className="text-[11px] font-semibold px-2.5 py-1 rounded-full"
      style={{ background: s.bg, color: s.text, border: `1px solid ${s.border}` }}
    >
      {label || timing}
    </span>
  )
}

// ── Skill gap section ─────────────────────────────────────────────────────────

const TIER_META = {
  core:      { label: '核心技能', color: '#dc2626', bg: 'rgba(220,38,38,0.10)',  border: 'rgba(220,38,38,0.25)',  badge: 'rgba(220,38,38,0.10)'  },
  important: { label: '重要技能', color: '#d97706', bg: 'rgba(217,119,6,0.10)',  border: 'rgba(217,119,6,0.25)',  badge: 'rgba(217,119,6,0.10)'  },
  bonus:     { label: '加分技能', color: '#2563eb', bg: 'rgba(37,99,235,0.08)',  border: 'rgba(37,99,235,0.25)',  badge: 'rgba(37,99,235,0.08)'  },
}

const POSITIONING_META = {
  junior: { color: '#d97706', bg: 'rgba(217,119,6,0.10)',  border: 'rgba(217,119,6,0.30)'  },
  mid:    { color: '#2563eb', bg: 'rgba(37,99,235,0.10)',  border: 'rgba(37,99,235,0.30)'  },
  senior: { color: '#16a34a', bg: 'rgba(22,163,74,0.10)',  border: 'rgba(22,163,74,0.30)'  },
}

const POSITIONING_FALLBACK = {
  color: '#64748b', bg: 'rgba(100,116,139,0.10)', border: 'rgba(100,116,139,0.30)'
}

function TierBar({ tier, stats, hasProjectData }: { tier: keyof typeof TIER_META; stats: SkillGapTier; hasProjectData: boolean }) {
  const m = TIER_META[tier]
  const practicedPct = stats.matched > 0 ? Math.round((stats.practiced_count / stats.total) * 100) : 0
  const claimedPct   = stats.matched > 0 ? Math.round((stats.claimed_count   / stats.total) * 100) : 0

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-[12px] font-semibold" style={{ color: m.color }}>{m.label}</span>
        <div className="flex items-center gap-2">
          {hasProjectData && stats.matched > 0 && (
            <span className="text-[11px] text-slate-400">
              {stats.practiced_count > 0 && (
                <span style={{ color: '#16a34a' }}>{stats.practiced_count}实战</span>
              )}
              {stats.practiced_count > 0 && stats.claimed_count > 0 && <span> · </span>}
              {stats.claimed_count > 0 && (
                <span className="text-slate-400">{stats.claimed_count}待验证</span>
              )}
            </span>
          )}
          <span className="text-[12px] text-slate-500 tabular-nums">
            {stats.matched} / {stats.total}&ensp;<span className="font-semibold" style={{ color: m.color }}>{stats.pct}%</span>
          </span>
        </div>
      </div>
      {/* Split bar: green=practiced, color=claimed */}
      <div className="h-2 rounded-full overflow-hidden flex" style={{ background: 'rgba(148,163,184,0.15)' }}>
        {hasProjectData ? (
          <>
            <div className="h-full transition-all duration-700" style={{ width: `${practicedPct}%`, background: '#16a34a', opacity: 0.8 }} />
            <div className="h-full transition-all duration-700" style={{ width: `${claimedPct}%`, background: m.color, opacity: 0.45 }} />
          </>
        ) : (
          <div className="h-full rounded-full transition-all duration-700" style={{ width: `${stats.pct}%`, background: m.color, opacity: 0.75 }} />
        )}
      </div>
    </div>
  )
}

const STATUS_META = {
  completed: { label: '实战完成', color: '#16a34a', bg: 'rgba(22,163,74,0.10)', border: 'rgba(22,163,74,0.25)' },
  practiced: { label: '项目使用', color: '#2563eb', bg: 'rgba(37,99,235,0.10)', border: 'rgba(37,99,235,0.25)' },
  claimed:   { label: '待验证',   color: '#94a3b8', bg: 'rgba(148,163,184,0.12)', border: 'rgba(148,163,184,0.25)' },
}

function SkillGapSection({ gap }: { gap: SkillGap }) {
  const pm = POSITIONING_META[gap.positioning_level] || POSITIONING_FALLBACK
  const maxFreq = Math.max(...gap.top_missing.map(s => s.freq), 0.01)

  return (
    <div className="space-y-5">
      {/* Header + positioning */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <BarChart2 size={15} className="text-blue-500" />
          <span className="text-[13px] font-semibold text-slate-700">市场竞争力分析</span>
        </div>
        <span
          className="text-[12px] font-semibold px-3 py-1 rounded-full"
          style={{ background: pm.bg, color: pm.color, border: `1px solid ${pm.border}` }}
        >
          当前定位：{gap.positioning}
        </span>
      </div>

      {/* Tier coverage bars */}
      <div className="space-y-3.5">
        <TierBar tier="core"      stats={gap.core}      hasProjectData={gap.has_project_data} />
        <TierBar tier="important" stats={gap.important} hasProjectData={gap.has_project_data} />
        <TierBar tier="bonus"     stats={gap.bonus}     hasProjectData={gap.has_project_data} />
      </div>

      {/* Legend when project data exists */}
      {gap.has_project_data && (
        <div className="flex items-center gap-4 text-[11px] text-slate-400">
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-2.5 h-2 rounded-sm" style={{ background: '#16a34a', opacity: 0.8 }} />
            实战验证
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-2.5 h-2 rounded-sm" style={{ background: '#94a3b8', opacity: 0.45 }} />
            简历声称（待项目验证）
          </span>
        </div>
      )}

      {/* Matched skills — show what user has with proficiency badges */}
      {gap.matched_skills && gap.matched_skills.length > 0 && (
        <div>
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-2.5">
            你已掌握的技能
          </p>
          <div className="flex flex-wrap gap-2">
            {gap.matched_skills.map(skill => {
              const sm = STATUS_META[skill.status]
              const tm = TIER_META[skill.tier]
              return (
                <div
                  key={skill.name}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl"
                  style={{ background: 'rgba(255,255,255,0.35)', border: '1px solid rgba(255,255,255,0.45)' }}
                  title={`${tm.label} · JD出现率${Math.round(skill.freq * 100)}%`}
                >
                  <span className="text-[12px] font-medium text-slate-700">{skill.name}</span>
                  {gap.has_project_data && (
                    <span
                      className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full"
                      style={{ background: sm.bg, color: sm.color, border: `1px solid ${sm.border}` }}
                    >
                      {sm.label}
                    </span>
                  )}
                </div>
              )
            })}
          </div>
          {gap.has_project_data && gap.matched_skills.some(s => s.status === 'claimed') && (
            <p className="text-[11px] text-slate-400 mt-2 flex items-center gap-1">
              <AlertCircle size={11} />
              「待验证」技能建议在项目中实际使用，以提升竞争力评分
            </p>
          )}
        </div>
      )}

      {/* Top missing skills */}
      {gap.top_missing.length > 0 && (
        <div>
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-3">
            优先补强技能（按岗位需求频率排序）
          </p>
          <div className="space-y-2.5">
            {gap.top_missing.map(skill => {
              const m = TIER_META[skill.tier]
              const barPct = Math.round((skill.freq / maxFreq) * 100)
              return (
                <div key={skill.name} className="flex items-center gap-3">
                  <div className="w-24 flex-shrink-0 text-[12px] font-medium text-slate-700 truncate">
                    {skill.name}
                  </div>
                  <div className="flex-1 flex items-center gap-2">
                    <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(148,163,184,0.15)' }}>
                      <div
                        className="h-full rounded-full transition-all duration-700"
                        style={{ width: `${barPct}%`, background: m.color, opacity: 0.65 }}
                      />
                    </div>
                    <span className="text-[11px] tabular-nums text-slate-500 w-10 text-right">
                      {Math.round(skill.freq * 100)}%
                    </span>
                  </div>
                  <span
                    className="text-[10px] font-semibold px-2 py-0.5 rounded-full flex-shrink-0"
                    style={{ background: m.bg, color: m.color, border: `1px solid ${m.border}` }}
                  >
                    {m.label}
                  </span>
                </div>
              )
            })}
          </div>
          <p className="text-[11px] text-slate-400 mt-3">
            频率 = 该技能出现在目标岗位 JD 中的比例，越高越优先掌握
          </p>
        </div>
      )}
    </div>
  )
}

// ── Empty state ────────────────────────────────────────────────────────────────

function EmptyState({ onGenerate, loading }: { onGenerate: () => void; loading: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6 text-center">
      <div className="glass p-8 max-w-sm w-full">
        <div className="g-inner flex flex-col items-center gap-4">
          <div className="w-14 h-14 rounded-2xl flex items-center justify-center"
            style={{ background: 'rgba(37,99,235,0.1)' }}>
            <BookOpen size={24} className="text-blue-600" />
          </div>
          <div>
            <p className="text-[16px] font-bold text-slate-800">职业生涯发展报告</p>
            <p className="text-[13px] text-slate-500 mt-1">
              基于你的能力画像和成长档案，AI 将生成专属职业发展分析报告
            </p>
          </div>
          <button
            onClick={onGenerate}
            disabled={loading}
            className="btn-cta w-full flex items-center justify-center gap-2 py-3 text-[14px] font-semibold cursor-pointer disabled:opacity-60"
          >
            {loading ? (
              <><RefreshCw size={16} className="animate-spin" /> 生成中…</>
            ) : (
              <><Sparkles size={16} /> 生成我的报告</>
            )}
          </button>
          <p className="text-[11px] text-slate-400">
            需先完成「我的画像」设置 + 在「岗位图谱」设定职业目标
          </p>
        </div>
      </div>
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────────

const fadeUp = { hidden: { opacity: 0, y: 18 }, show: { opacity: 1, y: 0 } }
const container = { hidden: {}, show: { transition: { staggerChildren: 0.07 } } }

export default function ReportPage() {
  const queryClient = useQueryClient()
  const [editingNarrative, setEditingNarrative] = useState(false)
  const [narrativeDraft, setNarrativeDraft] = useState('')
  // activeReportId is derived from reports list — no local state needed.
  // Always show the most recent report; generation invalidates the list and picks up the new one.
  const [overrideReportId, setOverrideReportId] = useState<number | null>(null)

  // Fetch report list
  const { data: reports, isLoading: listLoading } = useQuery({
    queryKey: ['reports'],
    queryFn: fetchReportList,
  })

  const activeReportId = overrideReportId ?? reports?.[0]?.id ?? null

  // Fetch active report detail
  const { data: reportDetail, isLoading: detailLoading } = useQuery({
    queryKey: ['report', activeReportId],
    queryFn: () => fetchReportDetail(activeReportId!),
    enabled: activeReportId !== null,
  })

  // Generate report mutation
  const generateMut = useMutation({
    mutationFn: generateReport,
    onSuccess: (detail) => {
      setOverrideReportId(detail.id)
      queryClient.invalidateQueries({ queryKey: ['reports'] })
      queryClient.setQueryData(['report', detail.id], detail)
    },
    onError: (err: Error) => {
      alert(err.message || '报告生成失败，请确认已完成能力画像和职业目标设置')
    },
  })

  // Polish mutation
  const polishMut = useMutation({
    mutationFn: () => polishReport(activeReportId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['report', activeReportId] })
    },
  })

  // Edit save mutation
  const editMut = useMutation({
    mutationFn: () =>
      editReport(activeReportId!, { narrative_summary: narrativeDraft }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['report', activeReportId] })
      setEditingNarrative(false)
    },
  })

  // Delete report mutation
  const deleteMut = useMutation({
    mutationFn: () => deleteReport(activeReportId!),
    onSuccess: () => {
      setOverrideReportId(null)
      queryClient.removeQueries({ queryKey: ['report', activeReportId] })
      queryClient.invalidateQueries({ queryKey: ['reports'] })
    },
  })

  // Fetch staged plan with persistent check state
  const planQuery = useQuery({
    queryKey: ['report-plan', activeReportId],
    queryFn: () => fetchPlan(activeReportId!),
    enabled: !!activeReportId,
  })

  // Mutation for toggling plan check items
  const checkMut = useMutation({
    mutationFn: ({ itemId, done }: { itemId: string; done: boolean }) =>
      updatePlanCheck(activeReportId!, itemId, done),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['report-plan', activeReportId] })
    },
  })

  const isLoading = listLoading || detailLoading

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw size={20} className="animate-spin text-blue-500" />
          <p className="text-[13px] text-slate-500">加载中…</p>
        </div>
      </div>
    )
  }

  if (!reports || reports.length === 0 || !reportDetail) {
    return (
      <div className="max-w-[900px] mx-auto px-4 py-8">
        <EmptyState
          onGenerate={() => generateMut.mutate()}
          loading={generateMut.isPending}
        />
      </div>
    )
  }

  const rawData = reportDetail.data as Partial<ReportData> | undefined
  const data: ReportData | null =
    rawData && typeof rawData.match_score === 'number'
      ? (rawData as ReportData)
      : null

  if (!data) {
    return (
      <div className="max-w-[900px] mx-auto px-4 py-8 text-center">
        <p className="text-slate-500 mb-4">报告数据异常，请尝试重新生成</p>
        <button
          onClick={() => generateMut.mutate()}
          className="btn-cta px-4 py-2 text-[14px] font-semibold cursor-pointer"
        >
          重新生成报告
        </button>
      </div>
    )
  }

  const narrative = editingNarrative ? narrativeDraft : (data.narrative ?? '')

  const radarAllDims = [
    { dim: '基础要求', value: data.four_dim?.foundation, fullMark: 100 },
    { dim: '职业技能', value: data.four_dim?.skills,     fullMark: 100 },
    { dim: '职业素养', value: data.four_dim?.qualities,  fullMark: 100 },
    { dim: '发展潜力', value: data.four_dim?.potential,  fullMark: 100 },
  ]
  const radarData = radarAllDims.filter(d => d.value !== null && d.value !== undefined) as { dim: string; value: number; fullMark: number }[]
  const radarMissingDims = radarAllDims.filter(d => d.value === null || d.value === undefined).map(d => d.dim)

  // Derive checked set from plan API (persistent) — no local state needed
  const checkedItems = new Set(
    Object.entries(planQuery.data?.checked ?? {})
      .filter(([, v]) => v)
      .map(([k]) => k)
  )

  const planStages = planQuery.data?.stages ?? data.action_plan?.stages
  const allActionItems = planStages
    ? planStages.flatMap(s => s.items)
    : [
        ...(data.action_plan?.skills ?? []),
        ...(data.action_plan?.project ?? []),
        ...(data.action_plan?.job_prep ?? []),
      ]
  const doneCount = allActionItems.filter(a => checkedItems.has(a.id)).length

  function toggleCheck(id: string) {
    if (checkMut.isPending) return
    const newDone = !checkedItems.has(id)
    checkMut.mutate({ itemId: id, done: newDone })
  }

  return (
    <div className="relative min-h-screen">
      <style>{`
        @media print {
          body * { visibility: hidden; }
          #report-print-area, #report-print-area * { visibility: visible; }
          #report-print-area { position: absolute; left: 0; top: 0; width: 100%; }
          .no-print { display: none !important; }
          .glass, .glass-static { backdrop-filter: none !important; background: white !important;
            box-shadow: none !important; border: 1px solid #e2e8f0 !important; }
          body { background: white !important; }
        }
      `}</style>

      <div id="report-print-area" className="max-w-[900px] mx-auto px-4 py-8">
        <motion.div variants={container} initial="hidden" animate="show" className="flex flex-col gap-6">

          {/* ── Title + toolbar ── */}
          <motion.div variants={fadeUp} className="flex items-center justify-between">
            <div className="flex flex-col gap-1">
              <h1 className="text-[22px] font-bold text-slate-800">{reportDetail.title}</h1>
              {/* Report history selector + delete */}
              <div className="flex items-center gap-1.5">
                {reports.length > 1 ? (
                  <select
                    value={String(activeReportId ?? '')}
                    onChange={e => setOverrideReportId(Number(e.target.value))}
                    className="text-[12px] text-slate-500 bg-transparent border border-slate-200 rounded-md px-2 py-0.5 cursor-pointer w-fit"
                  >
                    {reports.map((r, i) => {
                      const d = new Date(r.created_at)
                      const ts = `${d.getMonth()+1}/${d.getDate()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
                      const score = r.match_score != null ? ` · ${r.match_score}分` : ''
                      return (
                        <option key={r.id} value={String(r.id)}>
                          {i === 0 ? `最新${score} · ${ts}` : `${ts}${score}`}
                        </option>
                      )
                    })}
                  </select>
                ) : (
                  <p className="text-[12px] text-slate-400">
                    生成于 {new Date(reportDetail.created_at).toLocaleDateString('zh-CN')}
                  </p>
                )}
                <button
                  onClick={() => {
                    if (confirm('确认删除这份报告？')) deleteMut.mutate()
                  }}
                  disabled={deleteMut.isPending}
                  title="删除此报告"
                  className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] text-slate-400 border border-slate-200 hover:text-red-500 hover:border-red-300 hover:bg-red-50 transition-colors cursor-pointer disabled:opacity-40"
                >
                  <Trash2 size={11} />
                  删除
                </button>
              </div>
            </div>
            <div className="flex gap-2 no-print">
              <button
                onClick={() => {
                  setEditingNarrative(v => !v)
                  if (!editingNarrative) setNarrativeDraft(data.narrative ?? '')
                }}
                className="btn-glass flex items-center gap-1.5 px-3.5 py-2 text-[13px] font-medium text-slate-600 cursor-pointer"
              >
                <Edit3 size={14} />
                编辑
              </button>
              <button
                onClick={() => polishMut.mutate()}
                disabled={polishMut.isPending}
                className="btn-glass flex items-center gap-1.5 px-3.5 py-2 text-[13px] font-medium text-slate-600 cursor-pointer disabled:opacity-60"
              >
                <Sparkles size={14} className={polishMut.isPending ? 'animate-spin text-blue-400' : 'text-blue-500'} />
                {polishMut.isPending ? '润色中…' : 'AI 润色'}
              </button>
              <button
                onClick={() => generateMut.mutate()}
                disabled={generateMut.isPending}
                className="btn-glass flex items-center gap-1.5 px-3.5 py-2 text-[13px] font-medium text-slate-600 cursor-pointer disabled:opacity-60"
              >
                <RefreshCw size={14} className={generateMut.isPending ? 'animate-spin' : ''} />
                {reports && reports.length > 0 ? '更新报告' : '生成报告'}
              </button>
              <button
                onClick={() => window.print()}
                className="btn-cta flex items-center gap-1.5 px-3.5 py-2 text-[13px] font-semibold cursor-pointer"
              >
                <Download size={14} />
                导出报告
              </button>
            </div>
          </motion.div>

          {/* ── AI Narrative — first thing student reads ── */}
          <motion.div variants={fadeUp} className="glass p-5">
            <div className="g-inner">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Sparkles size={15} className="text-blue-500" />
                  <span className="text-[13px] font-semibold text-slate-700">AI 综合评价</span>
                </div>
                {editingNarrative && (
                  <button
                    onClick={() => editMut.mutate()}
                    disabled={editMut.isPending}
                    className="btn-cta text-[12px] px-3 py-1 cursor-pointer disabled:opacity-60"
                  >
                    {editMut.isPending ? '保存中…' : '保存'}
                  </button>
                )}
              </div>
              {editingNarrative ? (
                <textarea
                  value={narrativeDraft}
                  onChange={e => setNarrativeDraft(e.target.value)}
                  className="w-full text-[13px] text-slate-700 leading-relaxed bg-white/50 border border-white/40 rounded-xl p-3 resize-none outline-none focus:border-blue-300"
                  rows={5}
                />
              ) : (
                <p className="text-[13px] text-slate-700 leading-[1.75]">{narrative}</p>
              )}
            </div>
          </motion.div>

          {/* ── Hero: Positioning + score ── */}
          <motion.div variants={fadeUp} className="glass p-6">
            <div className="g-inner flex flex-col gap-6">
              {/* Hero: Positioning */}
              <div className="flex items-center gap-6">
                <div className="flex-1">
                  <p className="text-[11px] text-slate-400 mb-1">你的市场定位</p>
                  <h2 className="text-xl font-bold text-slate-800">
                    {data.positioning || `${data.target?.label}`}
                  </h2>
                  <p className="text-[13px] text-slate-500 mt-1">
                    {data.skill_gap?.core && `核心技能覆盖 ${data.skill_gap.core.pct}%`}
                    {data.skill_gap?.top_missing && data.skill_gap.top_missing.length > 0 &&
                      `，补齐 ${data.skill_gap.top_missing.slice(0, 2).map(s => s.name).join('、')} 即可进阶`}
                  </p>
                  {data.market && (
                    <div className="mt-2">
                      <TimingBadge timing={data.market.timing} label={data.market.timing_label} />
                    </div>
                  )}
                </div>
                <ScoreRing score={data.match_score ?? 0} size={100} />
              </div>

              <div className="hidden sm:block h-px w-full bg-white/40" />

              <div className="flex-1 space-y-5">
                {/* Market row — always show all 3 cards */}
                {data.market && (
                  <div className="grid grid-cols-3 gap-2">
                    <div className="glass-static px-3 py-3 flex items-center gap-2">
                      <TrendingUp size={14} className={
                        data.market.demand_change_pct === null ? 'text-slate-400'
                        : data.market.demand_change_pct >= 0 ? 'text-green-600' : 'text-red-500'
                      } />
                      <div className="min-w-0">
                        <p className="text-[10px] text-slate-500 whitespace-nowrap">市场需求变化</p>
                        {data.market.demand_change_pct !== null ? (
                          <p className={`text-[13px] font-bold tabular-nums ${data.market.demand_change_pct >= 0 ? 'text-green-700' : 'text-red-600'}`}>
                            {data.market.demand_change_pct > 0 ? '+' : ''}{data.market.demand_change_pct.toFixed(0)}%
                          </p>
                        ) : (
                          <p className="text-[13px] font-bold text-slate-400">—</p>
                        )}
                      </div>
                    </div>

                    <div className="glass-static px-3 py-3 flex items-center gap-2">
                      <ArrowUpRight size={14} className={data.market.salary_cagr === null ? 'text-slate-400' : 'text-blue-600'} />
                      <div className="min-w-0">
                        <p className="text-[10px] text-slate-500 whitespace-nowrap">薪资年增长率</p>
                        {data.market.salary_cagr !== null ? (
                          <p className="text-[13px] font-bold text-blue-700 tabular-nums">{data.market.salary_cagr.toFixed(1)}%</p>
                        ) : (
                          <p className="text-[13px] font-bold text-slate-400">—</p>
                        )}
                      </div>
                    </div>

                    <div className="glass-static px-3 py-3 flex items-center gap-2">
                      <Briefcase size={14} className="text-slate-500" />
                      <div className="min-w-0">
                        <p className="text-[10px] text-slate-500 whitespace-nowrap">市场中位月薪</p>
                        <p className="text-[13px] font-bold text-slate-700 tabular-nums">
                          {data.market.salary_p50 ? `${Math.round(data.market.salary_p50 / 1000)}k` : '—'}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* 4D dims */}
                <div>
                  <p className="text-[11px] text-slate-400 font-medium mb-2.5">四维匹配详情</p>
                  <div className="grid grid-cols-4 gap-2">
                    {([
                      ['基础要求', data.four_dim?.foundation],
                      ['职业技能', data.four_dim?.skills],
                      ['职业素养', data.four_dim?.qualities],
                      ['发展潜力', data.four_dim?.potential],
                    ] as [string, number | null][]).map(([label, val]) => (
                      <div key={label} className="glass-static py-3 px-2 flex flex-col items-center">
                        <DimBadge label={label} value={val ?? null} />
                      </div>
                    ))}
                  </div>
                  {data.four_dim?.qualities === null && (
                    <p className="text-[11px] text-slate-400 mt-2 flex items-center gap-1">
                      <AlertCircle size={11} />
                      「职业素养」需完成模拟面试后显示
                    </p>
                  )}
                </div>
              </div>
            </div>
          </motion.div>

          {/* ── Delta change summary ── */}
          {data.delta && (
            <motion.div variants={fadeUp} className="glass p-5">
              <div className="g-inner">
                <div className="flex items-center gap-2 mb-4">
                  <BarChart2 size={15} className="text-slate-500" />
                  <p className="text-[13px] font-semibold text-slate-700">
                    本次更新（vs {new Date(data.delta.prev_date).toLocaleDateString('zh-CN')}）
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {/* Progress */}
                  <div className="rounded-xl p-3" style={{ background: 'rgba(22,163,74,0.06)', border: '1px solid rgba(22,163,74,0.12)' }}>
                    <div className="flex items-center gap-1.5 mb-2">
                      <TrendingUp size={13} className="text-green-600" />
                      <p className="text-[12px] font-semibold text-green-700">进步</p>
                    </div>
                    {data.delta.score_change !== 0 && (
                      <p className="text-[12px] text-slate-600 mb-1">
                        匹配度 {data.delta.prev_score} → {data.delta.prev_score + data.delta.score_change}
                        <span className={`font-semibold ml-1 ${data.delta.score_change > 0 ? 'text-green-600' : 'text-red-500'}`}>
                          {data.delta.score_change > 0 ? '+' : ''}{data.delta.score_change}
                        </span>
                      </p>
                    )}
                    {data.delta.gained_skills.length > 0 && (
                      <p className="text-[12px] text-slate-600 mb-1">新增：{data.delta.gained_skills.join('、')}</p>
                    )}
                    {data.delta.plan_progress && (
                      <p className="text-[12px] text-slate-600">
                        计划 {data.delta.plan_progress.done}/{data.delta.plan_progress.total} 项完成
                      </p>
                    )}
                    {data.delta.score_change === 0 && data.delta.gained_skills.length === 0 && (
                      <p className="text-[12px] text-slate-400">暂无新增变化</p>
                    )}
                  </div>

                  {/* Gaps */}
                  <div className="rounded-xl p-3" style={{ background: 'rgba(217,119,6,0.06)', border: '1px solid rgba(217,119,6,0.12)' }}>
                    <div className="flex items-center gap-1.5 mb-2">
                      <AlertCircle size={13} className="text-amber-600" />
                      <p className="text-[12px] font-semibold text-amber-700">待提升</p>
                    </div>
                    {data.delta.still_missing.length > 0 ? (
                      <ul className="space-y-1.5">
                        {data.delta.still_missing.map((s, i) => (
                          <li key={i} className="text-[12px] text-slate-600 leading-relaxed">
                            {s}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-[12px] text-slate-400">核心技能已覆盖</p>
                    )}
                  </div>

                  {/* Next action */}
                  <div className="rounded-xl p-3" style={{ background: 'rgba(37,99,235,0.06)', border: '1px solid rgba(37,99,235,0.12)' }}>
                    <div className="flex items-center gap-1.5 mb-2">
                      <ArrowUpRight size={13} className="text-blue-600" />
                      <p className="text-[12px] font-semibold text-blue-700">下一步</p>
                    </div>
                    {data.delta.next_action ? (
                      <p className="text-[12px] text-slate-600 leading-relaxed">{data.delta.next_action}</p>
                    ) : (
                      <p className="text-[12px] text-slate-400">查看下方成长计划</p>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* ── Radar + Growth curve ── */}
          <motion.div variants={fadeUp} className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div className="glass p-5">
              <div className="g-inner">
                <p className="text-[13px] font-semibold text-slate-700 mb-4">四维能力雷达</p>
                <ResponsiveContainer width="100%" height={240}>
                  <RadarChart data={radarData} margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
                    <PolarGrid stroke="rgba(148,163,184,0.3)" />
                    <PolarAngleAxis
                      dataKey="dim"
                      tick={{ fontSize: 11, fill: '#64748b', fontFamily: 'Plus Jakarta Sans' }}
                    />

                    <Radar
                      name="匹配度" dataKey="value"
                      stroke="#2563eb" fill="#2563eb" fillOpacity={0.18} strokeWidth={2}
                    />
                    <Tooltip
                      formatter={(v) => [`${v} 分`, '匹配度']}
                      contentStyle={{ background: 'rgba(255,255,255,0.95)', border: '1px solid rgba(255,255,255,0.5)', borderRadius: 10, fontSize: 12 }}
                    />
                  </RadarChart>
                </ResponsiveContainer>
                {radarMissingDims.length > 0 && (
                  <p className="text-[11px] text-slate-400 mt-2 text-center">
                    {radarMissingDims.join('、')}暂无数据·完成模拟面试后解锁
                  </p>
                )}
              </div>
            </div>

            <div className="glass p-5">
              <div className="g-inner">
                <div className="flex items-center justify-between mb-4">
                  <p className="text-[13px] font-semibold text-slate-700">成长轨迹</p>
                  {data.growth_curve && data.growth_curve.length >= 2 && (
                    <span className="chip text-[11px] text-green-700 font-semibold">
                      {data.growth_curve[data.growth_curve.length - 1].score - data.growth_curve[0].score >= 0 ? '+' : ''}
                      {(data.growth_curve[data.growth_curve.length - 1].score - data.growth_curve[0].score).toFixed(1)}%
                    </span>
                  )}
                </div>
                {data.growth_curve && data.growth_curve.length > 0 ? (
                  <ResponsiveContainer width="100%" height={220}>
                    <AreaChart data={data.growth_curve} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="scoreGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#2563eb" stopOpacity={0.25} />
                          <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                      <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                      <Tooltip
                        formatter={(v) => [`${v}%`, 'Readiness']}
                        contentStyle={{ background: 'rgba(255,255,255,0.95)', border: '1px solid rgba(255,255,255,0.5)', borderRadius: 10, fontSize: 12 }}
                      />
                      <Area
                        type="monotone" dataKey="score"
                        stroke="#2563eb" strokeWidth={2.5} fill="url(#scoreGrad)"
                        dot={{ r: 3, fill: '#2563eb', strokeWidth: 0 }}
                        activeDot={{ r: 5, fill: '#2563eb' }}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[220px] flex items-center justify-center">
                    <p className="text-[12px] text-slate-400">积累更多成长记录后显示成长曲线</p>
                  </div>
                )}
              </div>
            </div>
          </motion.div>

          {/* ── Skill Gap / Market Competitiveness ── */}
          {data.skill_gap && (
            <motion.div variants={fadeUp} className="glass p-6">
              <div className="g-inner">
                <SkillGapSection gap={data.skill_gap} />
              </div>
            </motion.div>
          )}

          {/* ── Promotion path timeline ── */}
          {data.promotion_path && data.promotion_path.length > 0 && (
            <motion.div variants={fadeUp} className="glass p-5">
              <div className="g-inner">
                <p className="text-[13px] font-semibold text-slate-700 mb-4">职业发展路径（参考）</p>
                <div className="flex items-center gap-0 overflow-x-auto pb-2">
                  {data.promotion_path.map((step, i) => {
                    const isCurrentLevel = data.positioning_level === 'junior' ? i === 0
                      : data.positioning_level === 'mid' ? i === 1
                      : data.positioning_level === 'senior' ? i === 2 : false
                    const currentIdx = data.positioning_level === 'junior' ? 0 : data.positioning_level === 'mid' ? 1 : 2
                    return (
                      <div key={i} className="flex items-center flex-shrink-0">
                        <div className="flex flex-col items-center">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-bold ${
                            i <= currentIdx
                              ? 'bg-blue-500 text-white'
                              : 'bg-slate-100 text-slate-400'
                          }`}>
                            {i + 1}
                          </div>
                          <span className={`text-[10px] mt-1.5 max-w-[72px] text-center leading-tight ${
                            isCurrentLevel ? 'text-blue-600 font-semibold' : 'text-slate-500'
                          }`}>
                            {step.title}
                            {isCurrentLevel && <span className="block text-[9px] text-blue-400">← 你在这里</span>}
                          </span>
                        </div>
                        {i < data.promotion_path!.length - 1 && (
                          <div className={`w-8 h-0.5 mx-1 mt-[-16px] ${
                            i < currentIdx
                              ? 'bg-blue-400' : 'bg-slate-200'
                          }`} />
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            </motion.div>
          )}

          {/* ── Soft skills ── */}
          {data.soft_skills && Object.keys(data.soft_skills).length > 0 && (
            <motion.div variants={fadeUp} className="glass p-5">
              <div className="g-inner">
                <p className="text-[13px] font-semibold text-slate-700 mb-3">通用素质要求</p>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                  {Object.entries(data.soft_skills).map(([key, value]) => {
                    const labels: Record<string, string> = {
                      communication: '沟通能力',
                      learning: '学习能力',
                      resilience: '抗压能力',
                      innovation: '创新能力',
                      collaboration: '协作能力',
                    }
                    const level = value as number
                    return (
                      <div key={key} className="text-center">
                        <p className="text-[11px] text-slate-500 mb-1">{labels[key] || key}</p>
                        <div className="flex justify-center gap-0.5">
                          {[1, 2, 3, 4, 5].map(i => (
                            <div key={i} className={`w-2.5 h-2.5 rounded-full ${
                              i <= level ? 'bg-blue-500' : 'bg-slate-200'
                            }`} />
                          ))}
                        </div>
                        <p className="text-[10px] text-slate-400 mt-0.5">
                          {level <= 2 ? '基础' : level <= 3 ? '重要' : '核心'}
                        </p>
                      </div>
                    )
                  })}
                </div>
              </div>
            </motion.div>
          )}

          {/* ── Action Plan ── */}
          {(data.action_plan || planQuery.data) && (
            <motion.div variants={fadeUp} className="glass p-6">
              <div className="g-inner">
                {/* Header */}
                <div className="flex items-center justify-between mb-5">
                  <div className="flex items-center gap-2">
                    <Zap size={15} className="text-amber-500" />
                    <p className="text-[13px] font-semibold text-slate-700">个性化成长计划</p>
                  </div>
                  <span className="text-[11px] text-slate-400">
                    {doneCount} / {allActionItems.length} 已完成
                  </span>
                </div>

                {/* Progress bar */}
                {allActionItems.length > 0 && (
                  <div className="mb-5 h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(148,163,184,0.2)' }}>
                    <div className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${(doneCount / allActionItems.length) * 100}%`,
                        background: 'linear-gradient(90deg, #3b82f6, #6366f1)',
                      }} />
                  </div>
                )}

                {/* ── 个性化成长计划 ── */}
                {(() => {
                  // Prefer staged format from plan API, fallback to old format from report data
                  const stages = planQuery.data?.stages ?? data.action_plan?.stages

                  if (stages && stages.length > 0) {
                    // New staged display
                    return stages.map((stage) => {
                      const stageItems = stage.items || []
                      const stageDone = stageItems.filter(a => checkedItems.has(a.id)).length
                      const stageTotal = stageItems.length
                      const stageComplete = stageTotal > 0 && stageDone === stageTotal

                      return (
                        <div key={stage.stage} className="mb-6">
                          {/* Stage header */}
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                              <span className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold text-white ${stageComplete ? 'bg-green-500' : 'bg-blue-500'}`}>
                                {stage.stage}
                              </span>
                              <span className="text-[13px] font-semibold text-slate-700">{stage.label}</span>
                              <span className="text-[11px] text-slate-400">{stage.duration}</span>
                            </div>
                            <span className="text-[11px] tabular-nums text-slate-400">
                              {stageDone}/{stageTotal}
                            </span>
                          </div>

                          {/* Stage progress bar */}
                          <div className="h-1.5 bg-slate-100 rounded-full mb-2 overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-500"
                              style={{
                                width: `${stageTotal > 0 ? (stageDone / stageTotal) * 100 : 0}%`,
                                background: stageComplete ? '#16a34a' : '#2563eb',
                              }}
                            />
                          </div>

                          {/* Milestone */}
                          <p className="text-[11px] text-slate-400 mb-3 flex items-center gap-1">
                            <Target size={11} />
                            阶段目标：{stage.milestone}
                          </p>

                          {/* Stage complete banner */}
                          {stageComplete && (
                            <div className="bg-green-50 border border-green-200 rounded-lg p-2.5 mb-3 text-[12px] text-green-700 font-medium text-center">
                              本阶段已完成！
                            </div>
                          )}

                          {/* Task items */}
                          <div className="space-y-2">
                            {stageItems.map(item => {
                              const done = checkedItems.has(item.id)
                              return (
                                <button key={item.id} onClick={() => toggleCheck(item.id)}
                                  className="w-full text-left flex items-start gap-3 p-3 rounded-xl transition-all duration-200 cursor-pointer"
                                  style={{ background: done ? 'rgba(22,163,74,0.06)' : 'rgba(255,255,255,0.5)' }}
                                >
                                  <div className={`mt-0.5 w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-colors ${done ? 'bg-green-500 border-green-500' : 'border-slate-300'}`}>
                                    {done && <Check size={12} className="text-white" />}
                                  </div>
                                  <div className="flex-1 min-w-0">
                                    <p className={`text-[13px] leading-relaxed ${done ? 'text-slate-400 line-through' : 'text-slate-700'}`}>
                                      {item.text}
                                    </p>
                                    <div className="flex items-center gap-2 mt-1.5">
                                      <span className="chip text-[10px]" style={{
                                        background: item.priority === 'high' ? 'rgba(239,68,68,0.08)' : 'rgba(37,99,235,0.08)',
                                        color: item.priority === 'high' ? '#dc2626' : '#2563eb',
                                      }}>
                                        {item.tag}
                                      </span>
                                      {item.deliverable && (
                                        <span className="text-[10px] text-slate-400">
                                          产出物：{item.deliverable}
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                </button>
                              )
                            })}
                          </div>
                        </div>
                      )
                    })
                  }

                  // Fallback to old category-based format
                  return ([
                    { key: 'skills' as const,   label: '技能补强', icon: <Target size={13} className="text-blue-500" />,    color: 'rgba(59,130,246,0.08)',  border: 'rgba(59,130,246,0.15)' },
                    { key: 'project' as const,  label: '实战项目', icon: <FolderGit2 size={13} className="text-violet-500" />, color: 'rgba(139,92,246,0.08)', border: 'rgba(139,92,246,0.15)' },
                    { key: 'job_prep' as const, label: '求职准备', icon: <ClipboardList size={13} className="text-emerald-500" />, color: 'rgba(16,185,129,0.08)', border: 'rgba(16,185,129,0.15)' },
                  ] as const).map(({ key, label, icon, color, border }) => {
                    const items = data.action_plan?.[key] ?? []
                    if (items.length === 0) return null
                    return (
                      <div key={key}>
                        <div className="flex items-center gap-1.5 mb-2">
                          {icon}
                          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">{label}</span>
                        </div>
                        <div className="space-y-2">
                          {items.map(item => {
                            const done = checkedItems.has(item.id)
                            return (
                              <button key={item.id} onClick={() => toggleCheck(item.id)}
                                className="w-full text-left flex items-start gap-3 p-3 rounded-xl transition-all duration-200 cursor-pointer"
                                style={{
                                  background: done ? 'rgba(148,163,184,0.06)' : color,
                                  border: `1px solid ${done ? 'rgba(148,163,184,0.15)' : border}`,
                                  opacity: done ? 0.6 : 1,
                                }}
                              >
                                <div className="flex-shrink-0 mt-0.5 w-4 h-4 rounded-full border-2 flex items-center justify-center transition-all duration-200"
                                  style={{
                                    borderColor: done ? '#94a3b8' : '#3b82f6',
                                    background: done ? '#94a3b8' : 'transparent',
                                  }}
                                >
                                  {done && <Check size={9} className="text-white" strokeWidth={3} />}
                                </div>
                                <div className="flex-1 min-w-0">
                                  <p className={`text-[12px] leading-[1.6] ${done ? 'line-through text-slate-400' : 'text-slate-700'}`}>
                                    {item.text}
                                  </p>
                                  {item.tag && (
                                    <span className="inline-block mt-1 text-[10px] px-1.5 py-0.5 rounded-md font-medium"
                                      style={{ background: 'rgba(255,255,255,0.6)', color: '#64748b' }}>
                                      {item.tag}
                                    </span>
                                  )}
                                </div>
                                {item.priority === 'high' && !done && (
                                  <span className="flex-shrink-0 text-[10px] font-bold text-amber-500 mt-0.5">优先</span>
                                )}
                              </button>
                            )
                          })}
                        </div>
                      </div>
                    )
                  })
                })()}
              </div>
            </motion.div>
          )}

          {/* ── Footer ── */}
          <motion.div variants={fadeUp} className="pb-4">
            <div className="flex items-center gap-2 justify-center">
              <BookOpen size={12} className="text-slate-400" />
              <p className="text-[11px] text-slate-400">
                本报告由 AI 基于成长档案自动生成 · {new Date(reportDetail.created_at).toLocaleDateString('zh-CN')}
              </p>
            </div>
          </motion.div>

        </motion.div>
      </div>
    </div>
  )
}
