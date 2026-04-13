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
} from 'lucide-react'
import {
  fetchReportList, fetchReportDetail, generateReport,
  editReport, polishReport,
} from '@/api/report'

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
}

interface MissingSkill {
  name: string
  freq: number   // 0.0–1.0 JD frequency
  tier: 'core' | 'important' | 'bonus'
}

interface SkillGap {
  core: SkillGapTier
  important: SkillGapTier
  bonus: SkillGapTier
  top_missing: MissingSkill[]
  positioning: string
  positioning_level: 'junior' | 'mid' | 'senior'
}

interface ActionItem {
  id: string
  text: string
  hours: string
  done: boolean
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
  action_plan: { short: ActionItem[]; mid: ActionItem[] }
  target: { node_id: string; label: string; zone: string }
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function ScoreRing({ score }: { score: number }) {
  const r = 54
  const circ = 2 * Math.PI * r
  const offset = circ * (1 - score / 100)
  const color = score >= 75 ? '#16a34a' : score >= 50 ? '#2563eb' : '#f59e0b'

  return (
    <div className="relative flex items-center justify-center" style={{ width: 136, height: 136 }}>
      <svg width={136} height={136} className="-rotate-90">
        <circle cx={68} cy={68} r={r} fill="none" stroke="rgba(255,255,255,0.35)" strokeWidth={10} />
        <circle
          cx={68} cy={68} r={r} fill="none"
          stroke={color} strokeWidth={10} strokeLinecap="round"
          strokeDasharray={circ} strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 1.2s ease' }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-3xl font-bold text-slate-800 tabular-nums">{score}</span>
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

function TierBar({ tier, stats }: { tier: keyof typeof TIER_META; stats: SkillGapTier }) {
  const m = TIER_META[tier]
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-[12px] font-semibold" style={{ color: m.color }}>{m.label}</span>
        <span className="text-[12px] text-slate-500 tabular-nums">
          {stats.matched} / {stats.total}&ensp;<span className="font-semibold" style={{ color: m.color }}>{stats.pct}%</span>
        </span>
      </div>
      <div className="h-2 rounded-full overflow-hidden" style={{ background: 'rgba(148,163,184,0.15)' }}>
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${stats.pct}%`, background: m.color, opacity: 0.75 }}
        />
      </div>
    </div>
  )
}

function SkillGapSection({ gap }: { gap: SkillGap }) {
  const pm = POSITIONING_META[gap.positioning_level]
  // max freq of top_missing for relative bar width
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
        <TierBar tier="core"      stats={gap.core} />
        <TierBar tier="important" stats={gap.important} />
        <TierBar tier="bonus"     stats={gap.bonus} />
      </div>

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
  const [activeTab, setActiveTab] = useState<'short' | 'mid'>('short')
  const [checkedItems, setCheckedItems] = useState<Set<string>>(new Set())
  const [activeReportId, setActiveReportId] = useState<number | null>(null)

  // Fetch report list
  const { data: reports, isLoading: listLoading } = useQuery({
    queryKey: ['reports'],
    queryFn: fetchReportList,
    onSuccess: (data) => {
      if (data.length > 0 && activeReportId === null) {
        setActiveReportId(data[0].id)
      }
    },
  })

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
      queryClient.invalidateQueries({ queryKey: ['reports'] })
      setActiveReportId(detail.id)
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

  const data = reportDetail.data as ReportData
  const narrative = editingNarrative ? narrativeDraft : (data.narrative ?? '')

  const radarData = [
    { dim: '基础要求', value: data.four_dim?.foundation ?? 0, fullMark: 100 },
    { dim: '职业技能', value: data.four_dim?.skills ?? 0, fullMark: 100 },
    { dim: '职业素养', value: data.four_dim?.qualities ?? 0, fullMark: 100 },
    { dim: '发展潜力', value: data.four_dim?.potential ?? 0, fullMark: 100 },
  ]

  const actionItems = data.action_plan?.[activeTab] ?? []
  const totalHours = actionItems.reduce((s, a) => s + parseInt(a.hours ?? '0'), 0)
  const doneCount = actionItems.filter(a => checkedItems.has(a.id)).length

  function toggleCheck(id: string) {
    setCheckedItems(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div className="relative min-h-screen">
      <style>{`
        @media print {
          .no-print { display: none !important; }
          .glass, .glass-static { backdrop-filter: none !important; background: white !important;
            box-shadow: none !important; border: 1px solid #e2e8f0 !important; }
          body { background: white !important; }
        }
      `}</style>

      <div id="report-content" className="max-w-[900px] mx-auto px-4 py-8 space-y-6">
        <motion.div variants={container} initial="hidden" animate="show">

          {/* ── Title + toolbar ── */}
          <motion.div variants={fadeUp} className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-[22px] font-bold text-slate-800">{reportDetail.title}</h1>
              <p className="text-[13px] text-slate-500 mt-0.5">
                生成于 {new Date(reportDetail.created_at).toLocaleDateString('zh-CN')}
                {reports.length > 1 && (
                  <span className="ml-2 text-blue-500 cursor-pointer"
                    onClick={() => setActiveReportId(
                      reports[reports.findIndex(r => r.id === activeReportId) + 1]?.id ?? reports[0].id
                    )}>
                    查看历史报告
                  </span>
                )}
              </p>
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
                重新生成
              </button>
              <button
                onClick={() => window.print()}
                className="btn-cta flex items-center gap-1.5 px-3.5 py-2 text-[13px] font-semibold cursor-pointer"
              >
                <Download size={14} />
                导出 PDF
              </button>
            </div>
          </motion.div>

          {/* ── Hero: score + market + 4D dims ── */}
          <motion.div variants={fadeUp} className="glass p-6">
            <div className="g-inner flex flex-col sm:flex-row gap-6 items-start">
              <div className="flex flex-col items-center gap-3 min-w-[160px]">
                <ScoreRing score={data.match_score ?? 0} />
                <div className="flex flex-col items-center gap-1.5">
                  <span className="text-[15px] font-bold text-slate-800">{data.target?.label}</span>
                  {data.market && (
                    <TimingBadge timing={data.market.timing} label={data.market.timing_label} />
                  )}
                </div>
              </div>

              <div className="hidden sm:block w-px self-stretch bg-white/40" />

              <div className="flex-1 space-y-4">
                {/* Market row */}
                {data.market && (
                  <div className="flex flex-wrap gap-3">
                    {data.market.demand_change_pct !== null && (
                      <div className="glass-static px-4 py-2.5 flex items-center gap-2">
                        <TrendingUp size={15} className={data.market.demand_change_pct >= 0 ? 'text-green-600' : 'text-red-500'} />
                        <div>
                          <p className="text-[10px] text-slate-500">市场需求变化</p>
                          <p className={`text-[14px] font-bold ${data.market.demand_change_pct >= 0 ? 'text-green-700' : 'text-red-600'}`}>
                            {data.market.demand_change_pct > 0 ? '+' : ''}{data.market.demand_change_pct?.toFixed(0)}%
                          </p>
                        </div>
                      </div>
                    )}
                    {data.market.salary_cagr !== null && (
                      <div className="glass-static px-4 py-2.5 flex items-center gap-2">
                        <ArrowUpRight size={15} className="text-blue-600" />
                        <div>
                          <p className="text-[10px] text-slate-500">薪资年增长率</p>
                          <p className="text-[14px] font-bold text-blue-700">{data.market.salary_cagr?.toFixed(1)}%</p>
                        </div>
                      </div>
                    )}
                    <div className="glass-static px-4 py-2.5 flex items-center gap-2">
                      <Briefcase size={15} className="text-slate-500" />
                      <div>
                        <p className="text-[10px] text-slate-500">市场中位月薪</p>
                        <p className="text-[14px] font-bold text-slate-700">
                          {data.market.salary_p50 ? `${Math.round(data.market.salary_p50 / 1000)}k` : '—'}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* 4D dims */}
                <div>
                  <p className="text-[11px] text-slate-400 font-medium mb-3">四维匹配详情</p>
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

          {/* ── AI Narrative ── */}
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

          {/* ── Radar + Growth curve ── */}
          <motion.div variants={fadeUp} className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <div className="glass p-5">
              <div className="g-inner">
                <p className="text-[13px] font-semibold text-slate-700 mb-4">四维能力雷达</p>
                <ResponsiveContainer width="100%" height={220}>
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
                  <ResponsiveContainer width="100%" height={200}>
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
                  <div className="h-[200px] flex items-center justify-center">
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

          {/* ── Action Plan ── */}
          {data.action_plan && (
            <motion.div variants={fadeUp} className="glass p-6">
              <div className="g-inner">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Zap size={15} className="text-amber-500" />
                    <p className="text-[13px] font-semibold text-slate-700">个性化成长计划</p>
                  </div>
                  <div className="flex glass-static rounded-xl p-0.5 gap-0.5 no-print">
                    {(['short', 'mid'] as const).map(t => (
                      <button key={t} onClick={() => setActiveTab(t)}
                        className="px-3.5 py-1.5 text-[12px] font-medium rounded-lg transition-all duration-200 cursor-pointer"
                        style={{
                          background: activeTab === t ? 'rgba(255,255,255,0.8)' : 'transparent',
                          color: activeTab === t ? '#1e40af' : '#64748b',
                          boxShadow: activeTab === t ? '0 1px 4px rgba(0,0,0,0.08)' : 'none',
                        }}
                      >
                        {t === 'short' ? '近期 1–3月' : '中期 3–6月'}
                      </button>
                    ))}
                  </div>
                </div>

                <AnimatePresence mode="wait">
                  <motion.div key={activeTab}
                    initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.15 }}
                    className="space-y-1"
                  >
                    {actionItems.map(item => (
                      <button key={item.id} onClick={() => toggleCheck(item.id)}
                        className="w-full flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all duration-200 hover:bg-white/40 text-left"
                      >
                        <div className="flex-shrink-0 w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all duration-200"
                          style={{
                            borderColor: checkedItems.has(item.id) ? '#2563eb' : 'rgba(148,163,184,0.6)',
                            background: checkedItems.has(item.id) ? '#2563eb' : 'transparent',
                          }}
                        >
                          {checkedItems.has(item.id) && <Check size={11} className="text-white" strokeWidth={3} />}
                        </div>
                        <span className={`flex-1 text-[13px] ${checkedItems.has(item.id) ? 'line-through text-slate-400' : 'text-slate-700'}`}>
                          {item.text}
                        </span>
                        <span className="text-[11px] text-slate-400 font-medium tabular-nums">{item.hours}</span>
                      </button>
                    ))}
                  </motion.div>
                </AnimatePresence>

                <div className="mt-4 pt-4 border-t border-white/30 flex items-center justify-between">
                  <span className="text-[12px] text-slate-400">{doneCount} / {actionItems.length} 已完成</span>
                  <span className="text-[12px] text-slate-400">预计总投入：{totalHours}h</span>
                </div>
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
