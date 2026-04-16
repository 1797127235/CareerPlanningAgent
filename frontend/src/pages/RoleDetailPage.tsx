import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ChevronLeft, Check, AlertTriangle, ArrowRight, Shield, Zap, X, Briefcase, BarChart2, ClipboardList } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '@/hooks/useAuth'
import { rawFetch } from '@/api/client'
import { setCareerGoal } from '@/api/graph'
import { useProfileData } from '@/hooks/useProfileData'

/* ── Preference alignment helpers ── */
interface Preferences {
  work_style?: string
  value_priority?: string
  work_intensity?: string
  company_type?: string
  ai_attitude?: string
  current_stage?: string
}

interface AlignItem {
  label: string       // "你看重稳定"
  data: string        // "此方向需求增长26%，岗位数稳定"
  signal: 'match' | 'mixed' | 'note' | 'no_data'
}

function buildAlignItems(prefs: Preferences, data: RoleDetail): AlignItem[] {
  const items: AlignItem[] = []
  const rp = data.replacement_pressure ?? 50
  const zone = data.zone
  const sig = data.market_signal

  if (prefs.value_priority === 'stability') {
    const isStable = zone === 'safe' || (sig?.demand_trend === 'stable')
    const isGrowing = sig?.demand_trend === 'growing'
    items.push({
      label: '你看重稳定',
      data: isGrowing ? `此方向需求增长${sig?.demand_change_pct?.toFixed(0)}%，属于扩张期`
            : isStable ? '此方向需求相对平稳，竞争结构稳定'
            : `此方向需求近年有所收缩（${sig?.demand_change_pct?.toFixed(0)}%），竞争趋紧`,
      signal: isGrowing ? 'match' : isStable ? 'mixed' : 'note',
    })
  }

  if (prefs.value_priority === 'growth') {
    const sal = sig?.salary_momentum
    items.push({
      label: '你看重成长空间',
      data: sal === 'strong' ? `薪资年增${sig?.salary_cagr?.toFixed(0)}%，成长空间明显`
            : sal === 'moderate' ? `薪资温和增长（年均${sig?.salary_cagr?.toFixed(0)}%），成长稳健`
            : '此方向薪资增速较慢，成长空间有限',
      signal: sal === 'strong' ? 'match' : sal === 'moderate' ? 'mixed' : 'note',
    })
  }

  if (prefs.ai_attitude === 'avoid_ai') {
    items.push({
      label: '你想找AI替代不了的',
      data: rp < 30 ? `AI替代压力低（${rp}），人类判断力在此方向仍是核心`
            : rp < 55 ? `AI替代压力中等（${rp}），部分工作已被辅助，核心能力仍需人`
            : `AI替代压力较高（${rp}），需持续关注`,
      signal: rp < 30 ? 'match' : rp < 55 ? 'mixed' : 'note',
    })
  }

  if (prefs.ai_attitude === 'do_ai') {
    const aiRatio = sig?.ai_delta_pp ?? 0
    items.push({
      label: '你想拥抱AI方向',
      data: aiRatio >= 3 ? `AI需求快速渗透（+${aiRatio.toFixed(1)}pp），市场正在大量引入AI技能要求`
            : aiRatio >= 1 ? `AI影响在扩大（+${aiRatio.toFixed(1)}pp），方向在逐步转型`
            : `此方向AI渗透相对稳定，AI需求增量有限`,
      signal: aiRatio >= 3 ? 'match' : aiRatio >= 1 ? 'mixed' : 'note',
    })
  }

  if (prefs.company_type) {
    const employers = data.typical_employers ?? []
    const topInds = sig?.top_industries ?? []
    const indStr = topInds.slice(0, 2).map(i => i.industry?.slice(0, 8)).join('、')
    const compLabel: Record<string, string> = {
      big_tech: '大厂优先',
      growing: '成长型公司',
      startup: '初创团队',
      state_owned: '国企/事业单位',
    }
    items.push({
      label: `你倾向${compLabel[prefs.company_type] ?? prefs.company_type}`,
      data: employers.length > 0
        ? `典型招聘方：${employers.slice(0, 3).join('、')}${indStr ? `；主要行业：${indStr}` : ''}`
        : indStr ? `主要招聘行业：${indStr}` : '暂无雇主分布数据',
      signal: 'no_data',
    })
  }

  return items
}

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
  user_dynamic_level?: number
  user_matched_skills: string[]
  user_gap_skills: string[]
  match?: MatchResult | null
  // Market insight fields (from graph.json, always present)
  market_insight?: string
  ai_impact_narrative?: string
  typical_employers?: string[]
  entry_barrier?: 'low' | 'medium' | 'high'
  career_ceiling?: string
  distinguishing_features?: string[]
  // Market signal (from ETL precomputed signals)
  market_signal?: {
    demand_trend?: 'growing' | 'stable' | 'shrinking'
    demand_label?: string
    demand_change_pct?: number
    salary_momentum?: 'strong' | 'moderate' | 'flat'
    salary_label?: string
    salary_cagr?: number
    salary_p50_latest?: number
    ai_window?: 'accelerating' | 'growing' | 'stable'
    ai_label?: string
    ai_delta_pp?: number
    timing?: 'best' | 'good' | 'neutral' | 'caution' | 'no_data'
    timing_label?: string
    timing_reason?: string
    baseline_year?: number
    compare_year?: number
    top_industries?: Array<{ industry: string; count: number }>
    is_proxy?: boolean
    proxy_family?: string
  }
}

/* ── Constants ─────────────────────────────────────────────────────────── */

const ZONE_STYLE: Record<string, string> = {
  safe:       'bg-emerald-50 text-emerald-700 border-emerald-200',
  leverage:   'bg-blue-50 text-blue-700 border-blue-200',
  transition: 'bg-amber-50 text-amber-700 border-amber-200',
  danger:     'bg-red-50 text-red-700 border-red-200',
}
const ZONE_TEXT: Record<string, string> = {
  safe: '安全区', leverage: '杠杆区', transition: '过渡区', danger: '危险区',
}

/* ── Page ──────────────────────────────────────────────────────────────── */

export default function RoleDetailPage() {
  const { roleId } = useParams<{ roleId: string }>()
  const navigate = useNavigate()
  const { token } = useAuth()
  const { profile, loading: profileLoading } = useProfileData(token)

  const [data, setData] = useState<RoleDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [confirming, setConfirming] = useState(false)
  const [showGoalConfirm, setShowGoalConfirm] = useState(false)

  useEffect(() => {
    if (!roleId) {
      setLoading(false)
      setError('岗位ID不能为空')
      return
    }
    setLoading(true)
    setError(null)
    let cancelled = false
    rawFetch<RoleDetail>(`/graph/node/${encodeURIComponent(roleId)}`)
      .then((d) => { if (!cancelled) setData(d) })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : '加载失败') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [roleId])

  const hasRealProfile = !!(
    profile?.name?.trim() ||
    (profile?.profile?.skills?.length ?? 0) > 0
  )

  function handleExplore() {
    if (!data) return
    if (!hasRealProfile) {
      navigate('/profile?from=goal-set')
      return
    }
    // Show confirmation dialog instead of setting goal immediately
    setShowGoalConfirm(true)
  }

  async function handleConfirmGoal() {
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
      setShowGoalConfirm(false)
      navigate('/growth-log')
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

  if (error || !data) {
    return (
      <div className="max-w-[680px] mx-auto px-4 py-16 text-center">
        <p className="text-slate-500 mb-4">{error || '岗位不存在'}</p>
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

          {/* ── 市场动态 (来自真实招聘数据) ── */}
          {data.market_signal && data.market_signal.timing && data.market_signal.timing !== 'no_data' && (
            <>
              <div className="border-t border-slate-100" />
              <div>
                <SectionTitle>市场动态</SectionTitle>
                {/* Timing banner */}
                {(() => {
                  const t = data.market_signal!.timing
                  const cfg = {
                    best:    { bg: 'bg-emerald-50 border-emerald-200', dot: 'bg-emerald-500', text: 'text-emerald-800' },
                    good:    { bg: 'bg-blue-50 border-blue-200',       dot: 'bg-blue-500',    text: 'text-blue-800' },
                    neutral: { bg: 'bg-slate-50 border-slate-200',     dot: 'bg-slate-400',   text: 'text-slate-700' },
                    caution: { bg: 'bg-amber-50 border-amber-200',     dot: 'bg-amber-500',   text: 'text-amber-800' },
                  }
                  const s = cfg[t as keyof typeof cfg] ?? cfg.neutral
                  return (
                    <div className={`flex items-start gap-2.5 px-3.5 py-2.5 rounded-xl border mb-3 ${s.bg}`}>
                      <span className={`mt-1 w-2 h-2 rounded-full shrink-0 ${s.dot}`} />
                      <div>
                        <p className={`text-[13px] font-bold ${s.text}`}>{data.market_signal!.timing_label}</p>
                        <p className={`text-[11px] mt-0.5 ${s.text} opacity-80`}>{data.market_signal!.timing_reason}</p>
                        {data.market_signal!.is_proxy && (
                          <p className="text-[10px] text-slate-400 mt-0.5">* 参考「{data.market_signal!.proxy_family}」方向数据</p>
                        )}
                      </div>
                    </div>
                  )
                })()}
                {/* 3-metric row */}
                <div className="grid grid-cols-3 gap-2 mb-3">
                  {/* 需求趋势 */}
                  <div className="rounded-xl bg-slate-50 border border-slate-100 px-3 py-2">
                    <p className="text-[10px] text-slate-400 font-medium mb-1">需求趋势</p>
                    <p className={`text-[12px] font-bold ${
                      data.market_signal!.demand_trend === 'growing' ? 'text-emerald-600'
                      : data.market_signal!.demand_trend === 'stable' ? 'text-blue-600'
                      : 'text-amber-600'
                    }`}>
                      {data.market_signal!.demand_trend === 'growing' ? '↑ 上升' : data.market_signal!.demand_trend === 'stable' ? '→ 平稳' : '↓ 收缩'}
                      {data.market_signal!.demand_change_pct !== undefined && (
                        <span className="font-normal text-[10px] ml-1">
                          ({data.market_signal!.demand_change_pct > 0 ? '+' : ''}{data.market_signal!.demand_change_pct?.toFixed(0)}%)
                        </span>
                      )}
                    </p>
                    <p className="text-[10px] text-slate-400 mt-0.5">{data.market_signal!.baseline_year}→{data.market_signal!.compare_year}</p>
                  </div>
                  {/* 薪资动能 */}
                  <div className="rounded-xl bg-slate-50 border border-slate-100 px-3 py-2">
                    <p className="text-[10px] text-slate-400 font-medium mb-1">薪资动能</p>
                    <p className={`text-[12px] font-bold ${
                      data.market_signal!.salary_momentum === 'strong' ? 'text-emerald-600'
                      : data.market_signal!.salary_momentum === 'moderate' ? 'text-blue-600'
                      : 'text-slate-500'
                    }`}>
                      {data.market_signal!.salary_momentum === 'strong' ? '强劲增长' : data.market_signal!.salary_momentum === 'moderate' ? '温和增长' : '基本持平'}
                    </p>
                    <p className="text-[10px] text-slate-400 mt-0.5">年均 {data.market_signal!.salary_cagr?.toFixed(1)}%</p>
                  </div>
                  {/* AI渗透 */}
                  <div className="rounded-xl bg-slate-50 border border-slate-100 px-3 py-2">
                    <p className="text-[10px] text-slate-400 font-medium mb-1">AI渗透</p>
                    <p className={`text-[12px] font-bold ${
                      data.market_signal!.ai_window === 'accelerating' ? 'text-red-600'
                      : data.market_signal!.ai_window === 'growing' ? 'text-amber-600'
                      : 'text-slate-500'
                    }`}>
                      {data.market_signal!.ai_window === 'accelerating' ? '急速增长' : data.market_signal!.ai_window === 'growing' ? '持续扩大' : '相对稳定'}
                    </p>
                    <p className="text-[10px] text-slate-400 mt-0.5">{data.market_signal!.ai_delta_pp !== undefined ? `+${data.market_signal!.ai_delta_pp?.toFixed(1)}pp` : '-'}</p>
                  </div>
                </div>
                {/* Top industries */}
                {data.market_signal!.top_industries && data.market_signal!.top_industries!.length > 0 && (
                  <div>
                    <p className="text-[10px] text-slate-400 font-medium mb-1.5">招聘来源行业（2021-2024）</p>
                    <div className="flex flex-wrap gap-1.5">
                      {data.market_signal!.top_industries!.map((ind, i) => (
                        <span key={i} className="text-[11px] text-slate-600 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded-lg">
                          {ind.industry.length > 12 ? ind.industry.slice(0, 12) + '…' : ind.industry}
                          <span className="text-slate-400 ml-1">{ind.count.toLocaleString()}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </>
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
              <SectionTitle>学习资源</SectionTitle>
              <div className="text-[11px] text-slate-400 leading-relaxed">
                系统不直接提供学习内容。你可以在
                <button
                  onClick={() => navigate('/growth-log')}
                  className="text-[var(--blue)] hover:underline mx-1 cursor-pointer font-medium"
                >
                  成长档案
                </button>
                追踪实战项目进度，用项目驱动技能成长。
              </div>
            </div>
          </div>
          {/* ── 意愿对照 ── */}
          {(() => {
            const prefs = profile?.profile?.preferences as Preferences | undefined
            if (!prefs || !Object.values(prefs).some(Boolean)) return null
            const items = buildAlignItems(prefs, data)
            if (items.length === 0) return null
            const signalStyle = {
              match:   { dot: 'bg-emerald-400', text: 'text-slate-600' },
              mixed:   { dot: 'bg-amber-400',   text: 'text-slate-600' },
              note:    { dot: 'bg-slate-300',    text: 'text-slate-500' },
              no_data: { dot: 'bg-slate-200',    text: 'text-slate-400' },
            }
            return (
              <>
                <div className="border-t border-slate-100" />
                <div>
                  <SectionTitle>意愿对照</SectionTitle>
                  <div className="space-y-2.5">
                    {items.map((item, i) => {
                      const s = signalStyle[item.signal]
                      return (
                        <div key={i} className="flex items-start gap-2.5">
                          <span className={`mt-1.5 w-1.5 h-1.5 rounded-full shrink-0 ${s.dot}`} />
                          <div>
                            <span className="text-[12px] font-semibold text-slate-700">{item.label}</span>
                            <span className="text-[12px] text-slate-400 mx-1.5">—</span>
                            <span className={`text-[12px] ${s.text}`}>{item.data}</span>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </>
            )
          })()}

          {/* ── 市场洞察 ── */}
          {(data.market_insight || data.typical_employers?.length || data.ai_impact_narrative) && (
            <>
              <div className="border-t border-slate-100" />
              <div>
                <SectionTitle>市场洞察</SectionTitle>
                <div className="space-y-4">

                  {/* market_insight paragraph */}
                  {data.market_insight && (
                    <p className="text-[13px] text-slate-600 leading-[1.75]">{data.market_insight}</p>
                  )}

                  {/* 3-column meta row */}
                  {(data.entry_barrier || data.salary_p50 || data.typical_employers?.length) && (
                    <div className="grid grid-cols-3 gap-3">
                      {data.entry_barrier && (
                        <div className="rounded-xl bg-slate-50 border border-slate-100 px-3 py-2.5">
                          <p className="text-[10px] text-slate-400 font-medium mb-1">入门门槛</p>
                          <p className={`text-[13px] font-bold ${
                            data.entry_barrier === 'high' ? 'text-red-600'
                            : data.entry_barrier === 'medium' ? 'text-amber-600'
                            : 'text-emerald-600'
                          }`}>
                            {data.entry_barrier === 'high' ? '高' : data.entry_barrier === 'medium' ? '中' : '低'}
                          </p>
                        </div>
                      )}
                      {data.salary_p50 && (
                        <div className="rounded-xl bg-slate-50 border border-slate-100 px-3 py-2.5">
                          <p className="text-[10px] text-slate-400 font-medium mb-1">月薪中位数</p>
                          <p className="text-[13px] font-bold text-slate-700">{(data.salary_p50 / 1000).toFixed(0)}k</p>
                        </div>
                      )}
                      {data.typical_employers && data.typical_employers.length > 0 && (
                        <div className="rounded-xl bg-slate-50 border border-slate-100 px-3 py-2.5 col-span-1">
                          <p className="text-[10px] text-slate-400 font-medium mb-1">典型雇主</p>
                          <p className="text-[11px] text-slate-600 leading-snug">
                            {data.typical_employers.slice(0, 4).join(' · ')}
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* career_ceiling */}
                  {data.career_ceiling && (
                    <div className="rounded-xl bg-blue-50/50 border border-blue-100 px-4 py-3">
                      <p className="text-[10px] text-blue-400 font-bold uppercase tracking-wider mb-1.5">发展天花板</p>
                      <p className="text-[12px] text-slate-600 leading-[1.7]">{data.career_ceiling}</p>
                    </div>
                  )}

                  {/* ai_impact_narrative */}
                  {data.ai_impact_narrative && (
                    <div className="rounded-xl bg-amber-50/50 border border-amber-100 px-4 py-3">
                      <p className="text-[10px] text-amber-500 font-bold uppercase tracking-wider mb-1.5">AI 影响分析</p>
                      <p className="text-[12px] text-slate-600 leading-[1.7]">{data.ai_impact_narrative}</p>
                    </div>
                  )}

                </div>
              </div>
            </>
          )}

        </div>
      </div>

      {/* ── CTA ── */}
      {!profileLoading && (
        <div className="mt-5">
          {hasRealProfile ? (
            <>
              <button
                onClick={handleExplore}
                disabled={confirming}
                className="w-full py-3 rounded-xl bg-[var(--blue)] text-white text-[14px] font-semibold cursor-pointer hover:brightness-110 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {confirming ? '设定中...' : `开始探索「${data.label}」方向`}
              </button>
              <p className="text-[11px] text-slate-400 text-center mt-2">
                系统将追踪你与此方向的差距，随时可以更换
              </p>
            </>
          ) : (
            <>
              <button
                onClick={() => navigate('/profile?from=goal-set')}
                className="w-full py-3 rounded-xl bg-slate-100 text-slate-600 text-[14px] font-semibold cursor-pointer hover:bg-slate-200 transition-all border border-slate-200"
              >
                先建立画像，再设定目标
              </button>
              <p className="text-[11px] text-slate-400 text-center mt-2">
                上传简历后才能计算你与此方向的真实差距
              </p>
            </>
          )}
        </div>
      )}

      {/* ── Goal Confirmation Modal ── */}
      <AnimatePresence>
        {showGoalConfirm && data && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center p-6"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            onClick={() => { if (!confirming) setShowGoalConfirm(false) }}
          >
            {/* Backdrop */}
            <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-md" />

            {/* Card — higher opacity than glass-static (0.30) for legible modal text */}
            <motion.div
              className="relative max-w-[440px] w-full rounded-[24px] shadow-2xl p-7 space-y-5"
              style={{
                background: 'rgba(255,255,255,0.88)',
                backdropFilter: 'blur(32px) saturate(160%)',
                WebkitBackdropFilter: 'blur(32px) saturate(160%)',
                border: '1px solid rgba(255,255,255,0.70)',
                boxShadow: '0 8px 40px rgba(0,0,0,0.14), 0 1px 4px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.9)',
              }}
              initial={{ opacity: 0, scale: 0.88, y: 16 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.92, y: 8 }}
              transition={{ type: 'spring', damping: 22, stiffness: 320, mass: 0.8 }}
              onClick={e => e.stopPropagation()}
            >
              {/* Close button */}
              <button
                onClick={() => { if (!confirming) setShowGoalConfirm(false) }}
                className="absolute top-5 right-5 w-8 h-8 rounded-full bg-white/50 hover:bg-white/80 flex items-center justify-center text-slate-400 hover:text-slate-600 transition-all cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>

              {/* Header */}
              <div className="pr-8">
                <h3 className="text-[18px] font-extrabold text-slate-800">确认设定职业方向</h3>
                <p className="text-[12px] text-slate-400 mt-1">在此之前，请确认你理解这意味着什么</p>
              </div>

              {/* Direction badge */}
              <div className="bg-[var(--blue)]/8 border border-[var(--blue)]/20 rounded-2xl px-4 py-3.5 flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-[var(--blue)]/15 flex items-center justify-center shrink-0">
                  <Check className="w-4.5 h-4.5 text-[var(--blue)]" strokeWidth={2.5} />
                </div>
                <div>
                  <p className="text-[14px] font-extrabold text-slate-800">{data.label}</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">你选定的成长方向</p>
                </div>
              </div>

              {/* What this means — unified blue accent, clear semantic icons */}
              <div className="space-y-2">
                <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">设定后，系统会</p>
                {[
                  { Icon: Briefcase,     text: '优先为你推送这个方向的真实 JD 做诊断' },
                  { Icon: BarChart2,     text: 'Coach 持续追踪你与这个方向的技能差距' },
                  { Icon: ClipboardList, text: '成长档案按此目标记录你的项目和求职进展' },
                ].map(({ Icon, text }, i) => (
                  <div key={i} className="flex items-center gap-3 rounded-xl px-3.5 py-2.5 bg-slate-50 border border-slate-100">
                    <div className="w-8 h-8 rounded-xl bg-[var(--blue)]/10 flex items-center justify-center shrink-0">
                      <Icon className="w-4 h-4 text-[var(--blue)]" strokeWidth={1.8} />
                    </div>
                    <p className="text-[12.5px] text-slate-700 leading-relaxed">{text}</p>
                  </div>
                ))}
              </div>

              {/* Reassurance */}
              <p className="text-[11px] text-slate-400 text-center">
                方向可以随时更换，不会丢失已有的记录和诊断数据
              </p>

              {/* Actions */}
              <div className="flex gap-3">
                <button
                  onClick={() => setShowGoalConfirm(false)}
                  disabled={confirming}
                  className="flex-1 py-3 rounded-2xl text-[13px] font-semibold text-slate-600 bg-white/60 hover:bg-white/80 border border-white/60 transition-all cursor-pointer disabled:opacity-50"
                >
                  再想想
                </button>
                <button
                  onClick={handleConfirmGoal}
                  disabled={confirming}
                  className="flex-1 py-3 rounded-2xl text-[13px] font-bold text-white bg-[var(--blue)] hover:brightness-110 transition-all cursor-pointer disabled:opacity-60 shadow-lg shadow-blue-500/25"
                >
                  {confirming ? '设定中...' : '确认，开始追踪'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
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

function MatchBar({ label, score, detail: _detail, weight }: {
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
