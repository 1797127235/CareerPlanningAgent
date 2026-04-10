import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ChevronLeft, Check, AlertTriangle, ArrowRight, BookOpen, Shield, Zap } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { rawFetch } from '@/api/client'
import { setCareerGoal } from '@/api/graph'
import { useProfileData } from '@/hooks/useProfileData'

/* ── Types ─────────────────────────────────────────────────────────────── */

interface CareerTarget {
  node_id: string
  label: string
  zone: string
  career_level: number
}

interface MatchDimension {
  score: number
  detail: string
  weight: number
  matched?: string[]
}

interface MatchResult {
  total: number
  dimensions: {
    skill: MatchDimension
    potential: MatchDimension
    basic: MatchDimension
    soft_skill: MatchDimension
  }
}

interface RoleDetail {
  node_id: string
  label: string
  zone: string
  career_level: number
  replacement_pressure: number
  human_ai_leverage: number
  description?: string
  must_skills: string[]
  core_tasks: string[]
  promotion_path?: { level: number; title: string }[]
  salary_p50?: number
  intro?: string | null
  promotion_targets: CareerTarget[]
  transition_targets: CareerTarget[]
  learning_topic_count: number
  learning_progress?: { total_subtopics: number; completed: number; pct: number }
  user_dynamic_level?: number
  user_matched_skills: string[]
  user_gap_skills: string[]
  match?: MatchResult | null
}

/* ── Constants ─────────────────────────────────────────────────────────── */

const ZONE_STYLE: Record<string, string> = {
  safe:       'bg-emerald-50 text-emerald-700 border-emerald-200',
  thrive:     'bg-blue-50 text-blue-700 border-blue-200',
  transition: 'bg-amber-50 text-amber-700 border-amber-200',
  danger:     'bg-red-50 text-red-700 border-red-200',
}
const ZONE_TEXT: Record<string, string> = {
  safe: '安全区', thrive: '成长区', transition: '过渡区', danger: '风险区',
}

/* ── Page ──────────────────────────────────────────────────────────────── */

export default function RoleDetailPage() {
  const { roleId } = useParams<{ roleId: string }>()
  const navigate = useNavigate()
  const { token } = useAuth()
  const { profile, loading: profileLoading } = useProfileData(token)

  const [data, setData] = useState<RoleDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [confirming, setConfirming] = useState(false)

  useEffect(() => {
    if (!roleId) return
    setLoading(true)
    rawFetch<RoleDetail>(`/graph/node/${roleId}`)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [roleId])

  async function handleExplore() {
    if (!data || !profile) return
    setConfirming(true)
    try {
      await setCareerGoal({
        profile_id: profile.id,
        target_node_id: data.node_id,
        target_label: data.label,
        target_zone: data.zone,
        gap_skills: data.user_gap_skills || [],
        estimated_hours: 0,
        safety_gain: 0,
        salary_p50: data.salary_p50 || 0,
      })
      navigate('/profile/learning')
    } finally {
      setConfirming(false)
    }
  }

  if (loading) {
    return (
      <div className="max-w-[680px] mx-auto px-4 py-10">
        <div className="animate-pulse space-y-4">
          <div className="h-7 bg-slate-200 rounded w-2/5" />
          <div className="h-4 bg-slate-200 rounded w-3/5" />
          <div className="h-20 bg-slate-200 rounded-xl" />
          <div className="h-28 bg-slate-200 rounded-xl" />
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="max-w-[680px] mx-auto px-4 py-16 text-center">
        <p className="text-slate-500 mb-4">岗位不存在</p>
        <button onClick={() => navigate(-1)} className="text-[var(--blue)] font-medium cursor-pointer">返回</button>
      </div>
    )
  }

  const zone = data.zone
  const zoneStyle = ZONE_STYLE[zone] || 'bg-slate-50 text-slate-600 border-slate-200'
  const zoneText = ZONE_TEXT[zone] || zone
  const rp = data.replacement_pressure ?? 50
  const rpBadge = rp < 30 ? 'bg-emerald-50 text-emerald-700' : rp < 55 ? 'bg-amber-50 text-amber-700' : 'bg-red-50 text-red-700'
  const rpLabel = rp < 30 ? 'AI安全' : rp < 55 ? 'AI中等' : 'AI风险'

  const matchedCount = data.user_matched_skills.length
  const totalSkills = data.must_skills.length
  const hasMatch = matchedCount > 0 || data.user_gap_skills.length > 0

  return (
    <div className="max-w-[680px] mx-auto px-4 py-6 pb-12">
      {/* Back */}
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1 text-slate-400 hover:text-slate-600 text-[13px] font-medium mb-4 cursor-pointer transition-colors"
      >
        <ChevronLeft className="w-4 h-4" /> 返回
      </button>

      {/* ── Main card ── */}
      <div className="glass-static p-6">
        <div className="g-inner space-y-6">

          {/* Hero */}
          <div>
            <h1 className="text-[24px] font-bold text-slate-900 tracking-tight mb-1.5">{data.label}</h1>
            <div className="flex items-center gap-2 mb-3">
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${zoneStyle}`}>{zoneText}</span>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${rpBadge}`}>{rpLabel}</span>
            </div>
            {(data.intro || data.description) && (
              <p className="text-[13px] text-slate-500 leading-relaxed">{data.intro || data.description}</p>
            )}
          </div>

          {/* Divider */}
          <div className="border-t border-slate-100" />

          {/* 做什么 */}
          {data.core_tasks.length > 0 && (
            <div>
              <SectionTitle>做什么</SectionTitle>
              <div className="flex flex-wrap gap-1.5">
                {data.core_tasks.map((task, i) => (
                  <span key={i} className="text-[11px] text-slate-600 bg-slate-50 border border-slate-200 px-2.5 py-1 rounded-lg">
                    {task}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 人岗匹配分析 */}
          {data.match && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <SectionTitle>人岗匹配分析</SectionTitle>
                <div className="flex items-baseline gap-1">
                  <span className="text-[24px] font-black text-blue-600 leading-none">{data.match.total}</span>
                  <span className="text-[11px] text-slate-400">分</span>
                </div>
              </div>
              <div className="space-y-2.5">
                <MatchBar label="职业技能" score={data.match.dimensions.skill.score} detail={data.match.dimensions.skill.detail} weight={50} />
                <MatchBar label="发展潜力" score={data.match.dimensions.potential.score} detail={data.match.dimensions.potential.detail} weight={25} />
                <MatchBar label="基础要求" score={data.match.dimensions.basic.score} detail={data.match.dimensions.basic.detail} weight={15} />
                <MatchBar label="职业素养" score={data.match.dimensions.soft_skill.score} detail={data.match.dimensions.soft_skill.detail} weight={10} />
              </div>
              {/* Skill tags */}
              {(data.user_matched_skills.length > 0 || data.user_gap_skills.length > 0) && (
                <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-slate-50">
                  {data.user_matched_skills.map(s => (
                    <span key={s} className="inline-flex items-center gap-1 text-[10px] text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-lg">
                      <Check className="w-2.5 h-2.5" /> {s}
                    </span>
                  ))}
                  {data.user_gap_skills.map(s => (
                    <span key={s} className="inline-flex items-center gap-1 text-[10px] text-amber-600 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-lg">
                      <AlertTriangle className="w-2.5 h-2.5" /> {s}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Divider */}
          <div className="border-t border-slate-100" />

          {/* 往哪走 (双栏) */}
          {(data.promotion_path?.length || data.promotion_targets.length > 0 || data.transition_targets.length > 0) && (
            <div>
              <SectionTitle>往哪走</SectionTitle>
              <div className="grid grid-cols-2 gap-6">
                {/* 晋升阶梯 */}
                <div>
                  <h4 className="text-[10px] font-bold text-slate-300 uppercase tracking-wider mb-2">
                    晋升阶梯
                    {data.learning_progress && data.learning_progress.pct > 0 && (
                      <span className="ml-1 text-blue-400 normal-case tracking-normal">· 学习 {data.learning_progress.pct}%</span>
                    )}
                  </h4>
                  {data.promotion_path && data.promotion_path.length > 0 ? (() => {
                    const currentLevel = data.user_dynamic_level ?? 1
                    return (
                    <div>
                      {data.promotion_path!.map((step, i) => (
                        <div key={i} className="flex items-center gap-2">
                          <div className="flex flex-col items-center">
                            <div className={`w-2 h-2 rounded-full ${
                              step.level <= currentLevel ? 'bg-blue-500' : 'bg-slate-200'
                            }`} />
                            {i < data.promotion_path!.length - 1 && (
                              <div className={`w-px h-4 ${
                                step.level < currentLevel ? 'bg-blue-300' : 'bg-slate-200'
                              }`} />
                            )}
                          </div>
                          <span className={`text-[11px] leading-tight ${
                            step.level === currentLevel
                              ? 'font-bold text-blue-600'
                              : step.level < currentLevel
                                ? 'text-slate-400 line-through'
                                : 'text-slate-600'
                          }`}>
                            {step.title}
                            {step.level === currentLevel && (
                              <span className="text-[9px] ml-1 text-blue-400">← 你在这里</span>
                            )}
                          </span>
                        </div>
                      ))}
                    </div>
                    )
                  })() : data.promotion_targets.length > 0 ? (
                    <div className="space-y-1.5">
                      {data.promotion_targets.map(t => (
                        <NavLink key={t.node_id} label={t.label} onClick={() => navigate(`/roles/${t.node_id}`)} />
                      ))}
                    </div>
                  ) : (
                    <p className="text-[11px] text-slate-300">已是高级岗位</p>
                  )}
                </div>

                {/* 可转型方向 */}
                <div>
                  <h4 className="text-[10px] font-bold text-slate-300 uppercase tracking-wider mb-2">可转型方向</h4>
                  {data.transition_targets.length > 0 ? (
                    <div className="space-y-1.5">
                      {data.transition_targets.slice(0, 5).map(t => (
                        <div key={t.node_id} className="flex items-center gap-1.5">
                          <NavLink label={t.label} onClick={() => navigate(`/roles/${t.node_id}`)} />
                          <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded-full shrink-0 ${ZONE_STYLE[t.zone] || ''}`}>
                            {ZONE_TEXT[t.zone] || ''}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-[11px] text-slate-300">暂无数据</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Divider */}
          <div className="border-t border-slate-100" />

          {/* AI 趋势 + 学习路径 (双栏) */}
          <div className="grid grid-cols-2 gap-6">
            <div>
              <SectionTitle>AI 趋势</SectionTitle>
              <div className="space-y-2.5">
                <AiBar icon={<Shield className="w-3 h-3" />} label="替代压力" value={rp} low="低" high="高" invert />
                <AiBar icon={<Zap className="w-3 h-3" />} label="协作空间" value={data.human_ai_leverage} low="小" high="大" />
              </div>
              <p className="text-[9px] text-slate-300 mt-1.5">Anthropic Economic Index</p>
            </div>
            <div>
              <SectionTitle>学习路径</SectionTitle>
              {data.learning_topic_count > 0 ? (
                <button
                  onClick={() => navigate(`/explore/${data.node_id}/learning`)}
                  className="flex items-center gap-2 hover:text-[var(--blue)] transition-colors cursor-pointer group"
                >
                  <BookOpen className="w-3.5 h-3.5 text-blue-400" />
                  <span className="text-[12px] text-slate-500 group-hover:text-[var(--blue)]">{data.learning_topic_count} 个话题可学习 →</span>
                </button>
              ) : (
                <p className="text-[11px] text-slate-300">暂无学习路径</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── CTA ── */}
      {!profileLoading && profile && (
        <div className="mt-5">
          <button
            onClick={handleExplore}
            disabled={confirming}
            className="w-full py-3 rounded-xl bg-[var(--blue)] text-white text-[14px] font-semibold cursor-pointer hover:brightness-110 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {confirming ? '设定中...' : `开始探索「${data.label}」方向`}
          </button>
          <p className="text-[11px] text-slate-400 text-center mt-2">
            系统将生成差距分析和学习路径，随时可以更换方向
          </p>
        </div>
      )}
    </div>
  )
}

/* ── Shared components ─────────────────────────────────────────────────── */

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">{children}</h3>
}

function NavLink({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-1.5 text-[11px] text-slate-600 hover:text-blue-600 transition-colors cursor-pointer"
    >
      <ArrowRight className="w-3 h-3 text-slate-300" />
      {label}
    </button>
  )
}

function MatchBar({ label, score, detail, weight }: {
  label: string; score: number; detail: string; weight: number
}) {
  const color = score >= 80 ? 'bg-emerald-400' : score >= 60 ? 'bg-blue-400' : score >= 40 ? 'bg-amber-400' : 'bg-red-400'
  return (
    <div className="flex items-center gap-2">
      <span className="text-[11px] text-slate-600 w-16 shrink-0 font-medium">{label}</span>
      <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-[11px] font-bold text-slate-600 w-7 text-right tabular-nums">{score}</span>
      <span className="text-[9px] text-slate-300 w-8 text-right">{weight}%</span>
    </div>
  )
}

function AiBar({ icon, label, value, low, high, invert }: {
  icon: React.ReactNode; label: string; value: number; low: string; high: string; invert?: boolean
}) {
  const pct = Math.min(Math.max(value, 0), 100)
  const color = invert
    ? (pct <= 30 ? 'bg-emerald-400' : pct <= 60 ? 'bg-amber-400' : 'bg-red-400')
    : (pct >= 70 ? 'bg-emerald-400' : pct >= 40 ? 'bg-amber-400' : 'bg-red-400')
  const levelText = invert
    ? (pct <= 30 ? low : pct <= 60 ? '中' : high)
    : (pct >= 70 ? high : pct >= 40 ? '中' : low)
  const badgeCls = color === 'bg-emerald-400' ? 'bg-emerald-50 text-emerald-700'
    : color === 'bg-amber-400' ? 'bg-amber-50 text-amber-700'
    : 'bg-red-50 text-red-700'

  return (
    <div className="flex items-center gap-2">
      <span className="text-slate-400 shrink-0">{icon}</span>
      <span className="text-[11px] text-slate-500 w-16 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 rounded-full bg-slate-100 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] font-semibold text-slate-400 w-7 text-right tabular-nums">{pct}%</span>
      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${badgeCls}`}>{levelText}</span>
    </div>
  )
}
