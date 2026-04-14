/**
 * ReportPage — 职业生涯发展报告
 * Fetches real data from /api/report/. Falls back to generation prompt if no report exists.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ResponsiveContainer,
  Area, AreaChart, XAxis, YAxis, Tooltip,
} from 'recharts'
import {
  Sparkles, Download, Edit3, Check, Zap, BookOpen,
  ArrowUpRight, AlertCircle, RefreshCw, TrendingUp, BarChart2,
  Target, FolderGit2, ClipboardList, Trash2, ArrowRight, CircleAlert,
  Cpu, Wrench, Repeat,
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
  fill_path?: 'learn' | 'practice' | 'both'
  covered_by_project?: boolean
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

interface AlignmentItem {
  node_id: string
  label: string
  score: number        // 0-1
  evidence: string
  gap: string
}

interface CareerAlignment {
  observations: string
  alignments: AlignmentItem[]
  cannot_judge: string[]
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
  diagnosis?: {
    source: string
    source_type: 'resume' | 'growth_log'
    source_id: number | string
    current_text: string
    status: 'pass' | 'needs_improvement'
    highlight: string
    issues: string[]
    suggestion: string
  }[]
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
  soft_skills?: Record<string, number>
  career_alignment?: CareerAlignment | null
  differentiation_advice?: string
  ai_impact_narrative?: string
  project_recommendations?: {
    name: string
    why: string
    covered_skills?: string[]
  }[]
  project_mismatch?: boolean
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

// ── Career alignment section ─────────────────────────────────────────────────

function CareerAlignmentSection({ alignment }: { alignment: CareerAlignment | null | undefined }) {
  const navigate = useNavigate()

  // 兜底态：即使 alignment 为空，也显示基于目标方向的观察卡片，不写死「数据不足」
  if (!alignment) {
    return (
      <motion.div variants={fadeUp} className="glass p-5">
        <div className="g-inner">
          <div className="flex items-center gap-2 mb-2">
            <Target size={15} className="text-slate-400" />
            <p className="text-[13px] font-semibold text-slate-700">职业发展路径</p>
          </div>
          <p className="text-[12px] text-slate-500 leading-relaxed">
            基于当前档案标签与目标岗位做初步对齐观察。完善项目量化数据和技术文档后，分析精度会进一步提升。
          </p>
        </div>
      </motion.div>
    )
  }

  return (
    <motion.div variants={fadeUp} className="glass p-5">
      <div className="g-inner space-y-4">
        {/* Header with honesty label */}
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Target size={15} className="text-indigo-500" />
            <p className="text-[13px] font-semibold text-slate-700">职业发展路径</p>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">
              AI 观察 · 非预测
            </span>
          </div>
          <p className="text-[11px] text-slate-400">
            基于你的项目数据和技能画像做的事实对齐，不包含时间表或级别预测
          </p>
        </div>

        {/* Observations */}
        {alignment.observations && (
          <div className="text-[12.5px] text-slate-700 leading-relaxed px-3 py-2.5 bg-slate-50/60 rounded-lg">
            {alignment.observations}
          </div>
        )}

        {/* Alignments */}
        {alignment.alignments.length > 0 && (
          <div className="space-y-2.5">
            <p className="text-[11px] text-slate-500 font-medium">可能对齐的方向：</p>
            {alignment.alignments.map((a) => (
              <button
                key={a.node_id}
                onClick={() => navigate(`/roles/${a.node_id}`)}
                className="w-full text-left rounded-xl p-3.5 transition-all duration-200 hover:shadow-md cursor-pointer"
                style={{
                  background: 'rgba(99,102,241,0.06)',
                  border: '1px solid rgba(99,102,241,0.18)',
                }}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[13px] font-semibold text-slate-800">{a.label}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-indigo-600 tabular-nums">
                      对齐度 {Math.round(a.score * 100)}%
                    </span>
                    <ArrowRight size={12} className="text-indigo-400" />
                  </div>
                </div>
                {a.evidence && (
                  <p className="text-[11.5px] text-slate-600 leading-relaxed">
                    <span className="text-emerald-600">证据：</span>{a.evidence}
                  </p>
                )}
                {a.gap && (
                  <p className="text-[11.5px] text-slate-600 leading-relaxed mt-1">
                    <span className="text-amber-600">缺口：</span>{a.gap}
                  </p>
                )}
              </button>
            ))}
          </div>
        )}

        {/* Cannot judge */}
        {alignment.cannot_judge.length > 0 && (
          <div className="pt-3 border-t border-slate-100">
            <div className="flex items-start gap-1.5">
              <CircleAlert size={12} className="text-slate-400 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-[11px] text-slate-500 mb-1">系统无法判断的（需要你自己决策）：</p>
                <ul className="text-[11.5px] text-slate-600 space-y-0.5">
                  {alignment.cannot_judge.map((s, i) => (
                    <li key={i}>· {s}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
}

function AIImpactText({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false)
  const isLong = text.length > 250
  const displayText = expanded || !isLong ? text : text.slice(0, 200)

  return (
    <div className="text-[12.5px] text-slate-700 leading-relaxed px-3 py-2.5 bg-violet-50/40 rounded-lg border border-violet-100/60">
      {displayText}
      {isLong && !expanded && '…'}
      {isLong && (
        <button
          onClick={() => setExpanded(v => !v)}
          className="ml-1 text-[11px] text-violet-600 hover:underline"
        >
          {expanded ? '收起' : '展开更多'}
        </button>
      )}
    </div>
  )
}

// ── Skill gap section ─────────────────────────────────────────────────────────

const TIER_META = {
  core:      { label: '核心技能', color: '#64748b', bg: 'rgba(100,116,139,0.10)',  border: 'rgba(100,116,139,0.25)',  badge: 'rgba(100,116,139,0.10)'  },
  important: { label: '重要技能', color: '#d97706', bg: 'rgba(217,119,6,0.10)',  border: 'rgba(217,119,6,0.25)',  badge: 'rgba(217,119,6,0.10)'  },
  bonus:     { label: '加分技能', color: '#2563eb', bg: 'rgba(37,99,235,0.08)',  border: 'rgba(37,99,235,0.25)',  badge: 'rgba(37,99,235,0.08)'  },
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

function SkillChip({
  skill,
  accent,
}: {
  skill: MissingSkill
  accent: 'slate' | 'amber' | 'indigo' | 'violet'
}) {
  const styles = {
    slate: 'bg-slate-50 border-slate-200 text-slate-700',
    amber: 'bg-amber-50 border-amber-200 text-amber-900',
    indigo: 'bg-indigo-50 border-indigo-200 text-indigo-900',
    violet: 'bg-violet-50 border-violet-200 text-violet-900',
  }
  return (
    <span className={`relative inline-flex items-center px-2 py-1 rounded-md text-[11.5px] border ${styles[accent]}`}>
      {skill.covered_by_project && (
        <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-emerald-500" />
      )}
      <span className={skill.covered_by_project ? 'pr-1' : ''}>{skill.name}</span>
    </span>
  )
}

function SkillGapSection({ gap }: { gap: SkillGap }) {
  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-2">
        <BarChart2 size={15} className="text-blue-500" />
        <span className="text-[13px] font-semibold text-slate-700">市场竞争力分析</span>
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

      {/* Matched skills — simplified with left vertical line */}
      {gap.matched_skills && gap.matched_skills.length > 0 && (
        <div>
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-2.5">
            你已掌握的技能
          </p>
          <div className="flex flex-wrap gap-2">
            {gap.matched_skills.map(skill => {
              const sm = STATUS_META[skill.status]
              return (
                <span
                  key={skill.name}
                  className="relative px-2.5 py-1 rounded-md bg-white/60 text-[12px] text-slate-700 border border-slate-100"
                  title={`${TIER_META[skill.tier].label} · JD出现率${Math.round(skill.freq * 100)}%`}
                >
                  <span
                    className="absolute left-0 top-1.5 bottom-1.5 w-[2.5px] rounded-r-full"
                    style={{ background: sm.color }}
                  />
                  <span className="pl-1.5">{skill.name}</span>
                </span>
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

      {/* 缺口补法路径地图 */}
      {gap.top_missing && gap.top_missing.length > 0 && (
        <div className="space-y-4 mt-6 pt-4 border-t border-slate-100">
          <p className="text-[12px] font-semibold text-slate-700">缺口补法路径地图</p>

          {(() => {
            const learnSkills = gap.top_missing.filter((m: MissingSkill) => m.fill_path === 'learn')
            const practiceSkills = gap.top_missing.filter((m: MissingSkill) => m.fill_path === 'practice')
            const bothSkills = gap.top_missing.filter((m: MissingSkill) => m.fill_path === 'both')
            const coveredByProjectCount = gap.top_missing.filter((m: MissingSkill) => m.covered_by_project).length
            const totalMissing = gap.top_missing.length

            return (
              <>
                {/* 学习组 */}
                {learnSkills.length > 0 && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <BookOpen size={14} className="text-slate-500" />
                      <p className="text-[12.5px] font-semibold text-slate-700">
                        需要系统学习的概念（{learnSkills.length} 个）
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {learnSkills.map(s => (
                        <SkillChip key={s.name} skill={s} accent="slate" />
                      ))}
                    </div>
                    <div className="mt-2 p-2 rounded-md bg-slate-50/50 border border-slate-100 space-y-1">
                      <p className="text-[11px] text-slate-500 leading-relaxed">
                        <span className="font-medium text-slate-700">搜索建议：</span>
                        把上方概念换成「
                        {learnSkills.slice(0, 2).map(s => s.name).join(' / ')}
                        」+ 教程 / 面试 / 基础，在任意搜索引擎或技术社区检索即可。
                      </p>
                      <p className="text-[11px] text-slate-500 leading-relaxed">
                        系统路线图可参考开源项目
                        <a
                          href="https://github.com/jwasham/coding-interview-university/blob/main/translations/README-cn.md"
                          target="_blank"
                          rel="noreferrer"
                          className="text-blue-600 hover:underline"
                        >
                          coding-interview-university（中文版）
                        </a>
                        —— GitHub 341k star 的 CS 自学大纲，含数据结构、算法、系统等完整章节。
                      </p>
                    </div>
                  </div>
                )}

                {/* 实践组 */}
                {practiceSkills.length > 0 && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Wrench size={14} className="text-amber-600" />
                      <p className="text-[12.5px] font-semibold text-slate-700">
                        需要项目实践才能掌握（{practiceSkills.length} 个）
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {practiceSkills.map(s => (
                        <SkillChip key={s.name} skill={s} accent="amber" />
                      ))}
                    </div>
                    {coveredByProjectCount > 0 && (
                      <p className="text-[11px] text-amber-700 mt-1">
                        上方推荐的实战项目能覆盖其中 {coveredByProjectCount} 个
                      </p>
                    )}
                  </div>
                )}

                {/* 混合组 */}
                {bothSkills.length > 0 && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Repeat size={14} className="text-violet-500" />
                      <p className="text-[12.5px] font-semibold text-slate-700">
                        先学后做（{bothSkills.length} 个）
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {bothSkills.map(s => (
                        <SkillChip key={s.name} skill={s} accent="violet" />
                      ))}
                    </div>
                    <div className="mt-2 p-2 rounded-md bg-violet-50/40 border border-violet-100/50">
                      <p className="text-[11px] text-slate-500 leading-relaxed">
                        <span className="font-medium text-slate-700">搜索建议：</span>
                        先搜索「
                        {bothSkills.slice(0, 2).map(s => s.name).join(' / ')}
                        入门 / docs」理解概念，再通过项目落地。
                      </p>
                    </div>
                  </div>
                )}

                {/* 底部总结诚实话术 */}
                <div className="pt-3 border-t border-slate-100">
                  <p className="text-[11px] text-slate-500 leading-relaxed">
                    共 {totalMissing} 个缺口 · {coveredByProjectCount} 个可通过上方推荐项目补实践 ·{' '}
                    {totalMissing - coveredByProjectCount} 个需要通过系统学习或其他项目补齐。
                  </p>
                </div>
              </>
            )
          })()}
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
  const navigate = useNavigate()
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

          {/* ── Hero: 目标岗位 + 事实覆盖率 + 匹配分 ── */}
          <motion.div variants={fadeUp} className="glass p-6">
            <div className="g-inner flex flex-col gap-5">
              {/* 顶部：岗位名 + 匹配分小角落 + 核心覆盖 */}
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-[11px] text-slate-400 mb-1">目标岗位</p>
                  <h2 className="text-xl font-bold text-slate-800">
                    {data.target?.label || '未设定'}
                  </h2>
                  {data.skill_gap?.core && (
                    <p className="text-[13px] text-slate-500 mt-1">
                      核心技能 {data.skill_gap.core.matched}/{data.skill_gap.core.total} 覆盖
                      {data.skill_gap.has_project_data && ` · ${data.skill_gap.core.practiced_count} 个有项目证据`}
                    </p>
                  )}
                </div>
                <div className="flex flex-col items-end">
                  <ScoreRing score={data.match_score ?? 0} size={60} />
                  <p className="text-[10px] text-slate-400 mt-1">匹配度</p>
                </div>
              </div>

              {/* 中轴：AI 影响与护城河（Hero 核心内容） */}
              {data.ai_impact_narrative && (
                <div className="space-y-2 rounded-xl p-3.5 border border-violet-200/60 bg-violet-50/30">
                  <div className="flex items-center gap-2">
                    <Cpu size={13} className="text-violet-500" />
                    <p className="text-[12px] font-semibold text-slate-700">AI 影响与护城河</p>
                  </div>
                  <AIImpactText text={data.ai_impact_narrative} />
                </div>
              )}

              {/* mismatch 分支：诚实话术 */}
              {data.project_mismatch && (
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  当前画像和该岗位典型实战项目之间跨度较大。
                  可以从搜索
                  <span className="font-medium text-slate-700">「{data.target?.label} 学习路线」</span>
                  或
                  <span className="font-medium text-slate-700">「{data.target?.label} 入门教程」</span>
                  开始，补齐基础概念后再回看项目推荐。
                </p>
              )}

              {/* 市场 timing badge 保留但缩小 */}
              {data.market && (
                <div className="flex items-center gap-2">
                  <TimingBadge timing={data.market.timing} label={data.market.timing_label} />
                  <button
                    onClick={() => navigate(`/roles/${data.target?.node_id}`)}
                    className="text-[11px] text-blue-600 hover:underline"
                  >
                    查看岗位详情 →
                  </button>
                </div>
              )}
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

          {/* ── Growth curve ── */}
          <motion.div variants={fadeUp}>
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

          {/* ── Profile diagnosis ── */}
          {data.diagnosis && data.diagnosis.length > 0 && (
            <motion.div variants={fadeUp} className="glass p-6">
              <div className="g-inner">
                <div className="flex items-center gap-2 mb-4">
                  <ClipboardList size={15} className="text-amber-500" />
                  <p className="text-[13px] font-semibold text-slate-700">档案体检</p>
                </div>
                <div className="space-y-3">
                  {data.diagnosis.map((item, idx) => (
                    <div
                      key={idx}
                      className="rounded-xl p-4 transition-all duration-200"
                      style={{
                        background: item.status === 'pass' ? 'rgba(22,163,74,0.06)' : 'rgba(255,255,255,0.5)',
                        border: `1px solid ${item.status === 'pass' ? 'rgba(22,163,74,0.15)' : 'rgba(217,119,6,0.15)'}`,
                      }}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-[13px] font-medium text-slate-700">{item.source}</span>
                          <span
                            className="text-[10px] px-2 py-0.5 rounded-full"
                            style={{
                              background: item.source_type === 'resume' ? 'rgba(99,102,241,0.1)' : 'rgba(37,99,235,0.1)',
                              color: item.source_type === 'resume' ? '#6366f1' : '#2563eb',
                            }}
                          >
                            {item.source_type === 'resume' ? '简历' : '成长档案'}
                          </span>
                        </div>
                        <span
                          className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                          style={{
                            background: item.status === 'pass' ? 'rgba(22,163,74,0.1)' : 'rgba(217,119,6,0.1)',
                            color: item.status === 'pass' ? '#15803d' : '#b45309',
                          }}
                        >
                          {item.status === 'pass' ? '通过' : '还差一点'}
                        </span>
                      </div>
                      {item.status === 'needs_improvement' && (
                        <>
                          {item.highlight && (
                            <p className="text-[12px] text-slate-600 mb-1">
                              <span className="text-green-600 font-medium">亮点：</span>
                              {item.highlight}
                            </p>
                          )}
                          <p className="text-[12px] text-slate-600 mb-2">
                            <span className="text-amber-600 font-medium">差一步：</span>
                            {item.issues.join('、')}
                          </p>
                          {item.suggestion && (
                            <p className="text-[12px] text-indigo-600 px-3 py-2 rounded-lg bg-indigo-50/50 border border-indigo-100 leading-relaxed mb-2">
                              {item.suggestion}
                            </p>
                          )}
                          <div className="mt-3 flex justify-end">
                            <button
                              onClick={() => {
                                navigate('/growth-log?tab=refine')
                              }}
                              className="text-[12px] text-blue-600 hover:text-blue-700 font-medium cursor-pointer flex items-center gap-1 transition-colors duration-200"
                            >
                              去补充
                              <ArrowRight size={12} />
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {/* ── 职业发展路径（LLM 分析 + graph 绑定） ── */}
          <CareerAlignmentSection alignment={data.career_alignment} />

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
