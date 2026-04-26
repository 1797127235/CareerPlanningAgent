import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link, useSearchParams } from 'react-router-dom'
import { ChevronLeft, Check, AlertTriangle, ArrowRight, Shield, Zap, X, Briefcase, BarChart2, ClipboardList, MessageSquare } from 'lucide-react'
/* framer-motion removed — using CSS animations */
import { useAuth } from '@/hooks/useAuth'
import { rawFetch } from '@/api/client'
import { setCareerGoal } from '@/api/graph'
import { useProfileData } from '@/hooks/useProfileData'

/* ── Design Tokens ── */
const serif = { fontFamily: 'var(--font-serif), Georgia, "Noto Serif SC", serif' }
const sans = { fontFamily: 'var(--font-sans), "Noto Sans SC", system-ui, sans-serif' }
const ink = (n: 1 | 2 | 3) =>
  n === 1 ? 'var(--ink-1)' : n === 2 ? 'var(--ink-2)' : 'var(--ink-3)'

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
  contextual_narrative?: {
    what_you_actually_do: string
    what_drains_you: string
    three_year_outlook: string
    who_fits: string
    ai_impact_today: string
    common_entry_path: string
  }
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

const NARRATIVE_FIELDS = [
  { key: 'what_you_actually_do', label: '你每天真正在做的事' },
  { key: 'what_drains_you',      label: '什么会耗尽你' },
  { key: 'three_year_outlook',    label: '三年后的你' },
  { key: 'who_fits',              label: '适合什么样的人' },
  { key: 'ai_impact_today',       label: 'AI 对这个方向的影响' },
  { key: 'common_entry_path',     label: '常见入行路径' },
] as const

/* ── Constants ─────────────────────────────────────────────────────────── */

const ZONE_STYLE: Record<string, string> = {
  safe:       'bg-[#EEF5F0] text-[#5A8F6E] border-[#D4E5DA]',
  leverage:   'bg-[#FDF5E8] text-[#B85C38] border-[#EBDDD0]',
  transition: 'bg-[#FDF5E8] text-[#C4853F] border-[#EBDDD0]',
  danger:     'bg-[#FDF0EA] text-[#B85C38] border-[#EBDDD0]',
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
  const [searchParams] = useSearchParams()
  const isMock = searchParams.get('mock') === '1'

  const MOCK_ROLE_DETAIL: RoleDetail = {
    node_id: roleId || 'mock-role',
    label: '初级前端工程师',
    zone: 'safe',
    career_level: 1,
    replacement_pressure: 35,
    human_ai_leverage: 55,
    description: '负责 Web 前端页面的开发与维护，参与产品需求评审和技术方案设计。',
    must_skills: ['HTML/CSS', 'JavaScript', 'React/Vue', 'Git', 'TypeScript'],
    core_tasks: ['页面切图与还原', '组件开发与维护', '接口联调', '性能优化', '代码评审'],
    promotion_path: [
      { level: 1, title: '初级前端工程师' },
      { level: 2, title: '中级前端工程师' },
      { level: 3, title: '高级前端工程师' },
      { level: 4, title: '前端架构师' },
    ],
    salary_p50: 15000,
    intro: '前端开发是离用户最近的岗位，直接影响产品的使用体验。',
    promotion_targets: [
      { node_id: 'mid-frontend', label: '中级前端工程师', zone: 'safe', career_level: 2 },
      { node_id: 'fullstack', label: '全栈工程师', zone: 'transition', career_level: 2 },
    ],
    transition_targets: [
      { node_id: 'ui-designer', label: 'UI 设计师', zone: 'safe', career_level: 1 },
      { node_id: 'product-manager', label: '产品经理', zone: 'transition', career_level: 2 },
    ],
    user_dynamic_level: 1,
    user_matched_skills: ['HTML/CSS', 'JavaScript'],
    user_gap_skills: ['React/Vue', 'TypeScript', 'Git'],
    match: {
      total: 62,
      dimensions: {
        skill: { score: 70, detail: '已掌握基础前端技能', weight: 0.35 },
        potential: { score: 55, detail: '成长空间较大', weight: 0.25 },
        basic: { score: 80, detail: '学历和经验符合要求', weight: 0.25 },
        soft_skill: { score: 45, detail: '沟通和协作能力待提升', weight: 0.15 },
      },
    },
    market_insight: '前端开发需求稳定，React 和 Vue 生态持续活跃。',
    ai_impact_narrative: 'AI 辅助编码工具（Copilot 等）正在改变前端开发方式，但核心架构和设计能力仍不可替代。',
    typical_employers: ['互联网公司', '金融科技', '电商平台', 'SaaS 企业'],
    entry_barrier: 'low',
    career_ceiling: '技术总监 / 前端架构师',
    distinguishing_features: ['用户感知最强', '技术迭代快', '可视化成果'],
    contextual_narrative: {
      what_you_actually_do: '把设计师的稿子变成可交互的网页，处理各种浏览器兼容问题，和后端联调接口。',
      what_drains_you: '需求频繁变更、兼容性问题、加班赶进度。',
      three_year_outlook: '向全栈或前端架构方向发展，或者转型产品/设计。',
      who_fits: '喜欢视觉呈现、有耐心解决细节问题、愿意持续学习新技术的人。',
      ai_impact_today: 'AI 可以辅助写代码、生成页面，但复杂交互和架构设计仍需人工。',
      common_entry_path: '自学或培训班入门，通过实习或初级岗位积累经验。',
    },
    market_signal: {
      demand_trend: 'stable',
      demand_label: '需求平稳',
      demand_change_pct: 5,
      salary_momentum: 'moderate',
      salary_label: '薪资温和增长',
      salary_cagr: 8,
      salary_p50_latest: 15000,
      ai_window: 'growing',
      ai_label: 'AI 影响扩大中',
      ai_delta_pp: 12,
      timing: 'good',
      timing_label: '入行时机良好',
      timing_reason: '市场需求稳定，入门门槛较低',
      baseline_year: 2023,
      compare_year: 2024,
      top_industries: [
        { industry: '互联网', count: 1200 },
        { industry: '金融', count: 800 },
      ],
    },
  }

  useEffect(() => {
    if (!roleId) {
      setLoading(false)
      setError('岗位ID不能为空')
      return
    }
    if (isMock) {
      setLoading(true)
      setError(null)
      setTimeout(() => {
        setData(MOCK_ROLE_DETAIL)
        setLoading(false)
      }, 300)
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
  }, [roleId, isMock])

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
          <div className="h-7 rounded w-2/5" style={{ background: '#F0EBE5' }} />
          <div className="h-4 rounded w-3/5" style={{ background: '#F0EBE5' }} />
          <div className="h-20 rounded-xl" style={{ background: '#F0EBE5' }} />
          <div className="h-28 rounded-xl" style={{ background: '#F0EBE5' }} />
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="max-w-[680px] mx-auto px-4 py-16 text-center">
        <p className="mb-4" style={{ color: ink(3) }}>{error || '岗位不存在'}</p>
        <button onClick={() => navigate(-1)} className="font-medium cursor-pointer" style={{ color: 'var(--chestnut)' }}>返回</button>
      </div>
    )
  }

  const zone = data.zone
  const zoneStyle = ZONE_STYLE[zone] || 'bg-[var(--bg-paper)] text-[var(--ink-3)] border-[var(--line)]'
  const zoneText = ZONE_TEXT[zone] || zone
  const rp = data.replacement_pressure ?? 50
  const rpBadge = rp < 30 ? 'bg-[#EEF5F0] text-[#5A8F6E]' : rp < 55 ? 'bg-[#FDF5E8] text-[#C4853F]' : 'bg-[#FDF0EA] text-[#B85C38]'
  const rpLabel = rp < 30 ? 'AI安全' : rp < 55 ? 'AI中等' : 'AI风险'



  return (
    <div className="max-w-[680px] mx-auto px-4 py-6 pb-12">
      {/* Back */}
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1 text-[13px] font-medium mb-4 cursor-pointer transition-colors"
        style={{ color: ink(3), ...sans }}
        onMouseEnter={(e) => (e.currentTarget.style.color = ink(1))}
        onMouseLeave={(e) => (e.currentTarget.style.color = ink(3))}
      >
        <ChevronLeft className="w-4 h-4" /> 返回
      </button>

      {/* ── Main card ── */}
      <div className="rounded-2xl border border-[var(--line)] bg-[var(--bg-card)] p-6">
        <div className="space-y-8">

          {/* Hero */}
          <div>
            <h1 className="text-[clamp(22px,3vw,28px)] font-bold tracking-tight mb-1.5" style={{ ...serif, color: ink(1) }}>{data.label}</h1>
            <div className="flex items-center gap-2 mb-3">
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${zoneStyle}`}>{zoneText}</span>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${rpBadge}`}>{rpLabel}</span>
            </div>
            {(data.intro || data.description) && (
              <p className="text-[13px] leading-relaxed" style={{ ...sans, color: ink(2) }}>{data.intro || data.description}</p>
            )}
          </div>

          {/* 做什么 */}
          {data.core_tasks.length > 0 && (
            <div>
              <SectionTitle>做什么</SectionTitle>
              <div className="flex flex-wrap gap-2">
                {data.core_tasks.map((task, i) => (
                  <span
                    key={i}
                    className="text-[12px] px-3 py-1.5 rounded-lg border transition-colors hover:border-[var(--chestnut)]/30"
                    style={{ background: 'var(--bg-paper)', borderColor: 'var(--line)', color: ink(2), ...sans }}
                  >
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
                  <span className="text-[28px] font-bold leading-none" style={{ ...serif, color: '#3D2B1F' }}>{data.match.total}</span>
                  <span className="text-[11px]" style={{ color: ink(3), ...sans }}>分</span>
                </div>
              </div>
              <div className="space-y-3">
                <MatchBar label="职业技能" score={data.match.dimensions.skill.score} detail={data.match.dimensions.skill.detail} />
                <MatchBar label="发展潜力" score={data.match.dimensions.potential.score} detail={data.match.dimensions.potential.detail} />
                <MatchBar label="基础要求" score={data.match.dimensions.basic.score} detail={data.match.dimensions.basic.detail} />
                <MatchBar label="职业素养" score={data.match.dimensions.soft_skill.score} detail={data.match.dimensions.soft_skill.detail} />
              </div>
              {/* Skill tags */}
              {(data.user_matched_skills.length > 0 || data.user_gap_skills.length > 0) && (
                <div className="flex flex-wrap gap-2 mt-3 pt-3" style={{ borderTop: '1px solid var(--line)' }}>
                  {data.user_matched_skills.map(s => (
                    <span
                      key={s}
                      className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-lg border"
                      style={{ background: '#EEF5F0', borderColor: '#D4E5DA', color: '#5A8F6E', ...sans }}
                    >
                      <Check className="w-3 h-3" /> {s}
                    </span>
                  ))}
                  {data.user_gap_skills.map(s => (
                    <span
                      key={s}
                      className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-lg border"
                      style={{ background: '#FDF0EA', borderColor: '#EBDDD0', color: '#B85C38', ...sans }}
                    >
                      <AlertTriangle className="w-3 h-3" /> {s}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 发展方向 (双栏) */}
          {(data.promotion_path?.length || data.promotion_targets.length > 0 || data.transition_targets.length > 0) && (
            <div>
              <SectionTitle>发展方向</SectionTitle>
              <div className="grid grid-cols-2 gap-6">
                {/* 常见发展路径（参考） */}
                <div>
                  <h4 className="text-[10px] font-bold uppercase tracking-wider mb-2" style={{ color: ink(3), ...sans }}>
                    常见发展路径（参考）
                  </h4>
                  {data.promotion_path && data.promotion_path.length > 0 ? (
                    <div>
                      {data.promotion_path!.map((step, i) => (
                        <div key={i} className="flex items-center gap-2">
                          <div className="flex flex-col items-center">
                            <div className={`w-2 h-2 rounded-full ${
                              step.level <= (data.career_level ?? 2) ? 'bg-[var(--chestnut)]' : 'bg-[var(--line)]'
                            }`} />
                            {i < data.promotion_path!.length - 1 && (
                              <div className={`w-px h-4 ${
                                step.level < (data.career_level ?? 2) ? 'bg-[var(--chestnut)]/30' : 'bg-[var(--line)]'
                              }`} />
                            )}
                          </div>
                          <span className={`text-[11px] leading-tight ${
                            step.level === (data.career_level ?? 2)
                              ? 'font-bold'
                              : step.level < (data.career_level ?? 2)
                                ? 'line-through'
                                : ''
                          }`} style={{ color: step.level === (data.career_level ?? 2) ? 'var(--chestnut)' : step.level < (data.career_level ?? 2) ? ink(3) : ink(2), ...sans }}>
                            {step.title}
                          </span>
                        </div>
                      ))}
                      <p className="text-[9px] mt-2" style={{ color: ink(3), ...sans }}>不同公司职级体系差异较大，以上为行业常见路径参考</p>
                    </div>
                  ) : data.promotion_targets.length > 0 ? (
                    <div className="space-y-1.5">
                      {data.promotion_targets.map(t => (
                        <NavLink key={t.node_id} label={t.label} onClick={() => navigate(`/roles/${t.node_id}`)} />
                      ))}
                    </div>
                  ) : (
                    <p className="text-[11px]" style={{ color: ink(3), ...sans }}>已是高级岗位</p>
                  )}
                </div>

                {/* 可探索方向 */}
                <div>
                  <h4 className="text-[10px] font-bold uppercase tracking-wider mb-2" style={{ color: ink(3), ...sans }}>可探索方向</h4>
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
                    <p className="text-[11px]" style={{ color: ink(3), ...sans }}>暂无数据</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ── 市场动态 (来自真实招聘数据) ── */}
          {data.market_signal && data.market_signal.timing && data.market_signal.timing !== 'no_data' && (data.career_level ?? 2) < 4 && (
            <>
              <div className="border-t" style={{ borderColor: 'var(--line)' }} />
              <div>
                <div className="flex items-center justify-between mb-2">
                  <SectionTitle>市场动态</SectionTitle>
                  {data.market_signal!.is_proxy && (
                    <span className="text-[9px] px-2 py-0.5 rounded-full border" style={{ background: '#FDF5E8', borderColor: '#EBDDD0', color: '#C4853F', ...sans }}>
                      基于「{data.market_signal!.proxy_family}」方向估算
                    </span>
                  )}
                </div>
                {/* Timing banner */}
                {(() => {
                  const t = data.market_signal!.timing
                  const cfg = {
                    best:    { border: '#D4E5DA', accent: '#5A8F6E' },
                    good:    { border: '#EBDDD0', accent: '#C4853F' },
                    neutral: { border: 'var(--line)', accent: '#9CA3AF' },
                    caution: { border: '#EBDDD0', accent: '#B85C38' },
                  }
                  const s = cfg[t as keyof typeof cfg] ?? cfg.neutral
                  return (
                    <div className="flex items-start gap-2.5 px-3.5 py-2.5 rounded-xl border mb-3" style={{ background: 'var(--bg-paper)', borderColor: s.border }}>
                      <span className="mt-1 w-[3px] h-[3px] rounded-full shrink-0" style={{ background: s.accent }} />
                      <div>
                        <p className="text-[13px] font-bold" style={{ color: ink(1), ...sans }}>{data.market_signal!.timing_label}</p>
                        <p className="text-[11px] mt-0.5" style={{ color: ink(3), ...sans }}>{data.market_signal!.timing_reason}</p>
                      </div>
                    </div>
                  )
                })()}
                {/* 3-metric row */}
                <div className="grid grid-cols-3 gap-3 mb-3">
                  {/* 需求趋势 */}
                  <div>
                    <p className="text-[10px] font-medium mb-1" style={{ color: ink(3), ...sans }}>需求趋势</p>
                    <p className="text-[14px] font-bold" style={{ color: ink(1), ...sans }}>
                      {data.market_signal!.demand_trend === 'growing' ? '↑ 上升' : data.market_signal!.demand_trend === 'stable' ? '→ 平稳' : '↓ 收缩'}
                    </p>
                    {data.market_signal!.demand_change_pct !== undefined && (
                      <p className="text-[10px] mt-0.5" style={{ color: ink(3), ...sans }}>
                        {data.market_signal!.demand_change_pct > 0 ? '+' : ''}{data.market_signal!.demand_change_pct?.toFixed(0)}%
                      </p>
                    )}
                  </div>
                  {/* 薪资动能 */}
                  <div>
                    <p className="text-[10px] font-medium mb-1" style={{ color: ink(3), ...sans }}>薪资动能</p>
                    <p className="text-[14px] font-bold" style={{ color: ink(1), ...sans }}>
                      {data.market_signal!.salary_momentum === 'strong' ? '强劲增长' : data.market_signal!.salary_momentum === 'moderate' ? '温和增长' : '基本持平'}
                    </p>
                    <p className="text-[10px] mt-0.5" style={{ color: ink(3), ...sans }}>年均 {data.market_signal!.salary_cagr?.toFixed(1)}%</p>
                  </div>
                  {/* AI渗透 */}
                  <div>
                    <p className="text-[10px] font-medium mb-1" style={{ color: ink(3), ...sans }}>AI渗透</p>
                    <p className="text-[14px] font-bold" style={{ color: ink(1), ...sans }}>
                      {data.market_signal!.ai_window === 'accelerating' ? '急速增长' : data.market_signal!.ai_window === 'growing' ? '持续扩大' : '相对稳定'}
                    </p>
                    <p className="text-[10px] mt-0.5" style={{ color: ink(3), ...sans }}>{data.market_signal!.ai_delta_pp !== undefined ? `+${data.market_signal!.ai_delta_pp?.toFixed(1)}pp` : '-'}</p>
                  </div>
                </div>
                {/* Top industries */}
                {data.market_signal!.top_industries && data.market_signal!.top_industries!.length > 0 && (
                  <div>
                    <p className="text-[10px] font-medium mb-1.5" style={{ color: ink(3), ...sans }}>招聘来源行业</p>
                    <div className="flex flex-wrap gap-2">
                      {data.market_signal!.top_industries!.map((ind, i) => (
                        <span
                          key={i}
                          className="text-[11px] px-2 py-1 rounded-lg border"
                          style={{ background: 'var(--bg-paper)', borderColor: 'var(--line)', color: ink(2), ...sans }}
                        >
                          {ind.industry.length > 12 ? ind.industry.slice(0, 12) + '…' : ind.industry}
                          <span className="ml-1" style={{ color: ink(3) }}>{ind.count.toLocaleString()}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}

          {/* AI 趋势 + 学习路径 (双栏) */}
          <div className="grid grid-cols-2 gap-6">
            <div>
              <SectionTitle>AI 趋势</SectionTitle>
              <div className="space-y-3">
                <AiBar icon={<Shield className="w-3 h-3" />} label="替代压力" value={rp} low="低" high="高" invert />
                <AiBar icon={<Zap className="w-3 h-3" />} label="协作空间" value={data.human_ai_leverage} low="小" high="大" />
              </div>
              <p className="text-[9px] mt-1.5" style={{ color: ink(3), ...sans }}>Anthropic Economic Index</p>
            </div>
            <div>
              <SectionTitle>学习资源</SectionTitle>
              <div className="text-[12px] leading-relaxed" style={{ color: ink(2), ...sans }}>
                系统不直接提供学习内容。你可以在
                <button
                  onClick={() => navigate('/growth-log')}
                  className="cursor-pointer font-medium hover:underline mx-1"
                  style={{ color: 'var(--chestnut)' }}
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
            const signalStyle: Record<string, { dot: string; label: string }> = {
              match:   { dot: '#5A8F6E', label: ink(2) },
              mixed:   { dot: '#C4853F', label: ink(2) },
              note:    { dot: '#9CA3AF', label: ink(3) },
              no_data: { dot: '#D4C4B0', label: ink(3) },
            }
            return (
              <>
                <div className="border-t" style={{ borderColor: 'var(--line)' }} />
                <div>
                  <SectionTitle>意愿对照</SectionTitle>
                  <div className="space-y-2.5">
                    {items.map((item, i) => {
                      const s = signalStyle[item.signal]
                      return (
                        <div key={i} className="flex items-start gap-2.5">
                          <span className="mt-1.5 w-1.5 h-1.5 rounded-full shrink-0" style={{ background: s.dot }} />
                          <div>
                            <span className="text-[12px] font-semibold" style={{ color: ink(1), ...sans }}>{item.label}</span>
                            <span className="text-[12px] mx-1.5" style={{ color: ink(3) }}>—</span>
                            <span className="text-[12px]" style={{ color: s.label, ...sans }}>{item.data}</span>
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
              <div className="border-t" style={{ borderColor: 'var(--line)' }} />
              <div>
                <SectionTitle>市场洞察</SectionTitle>
                <div className="space-y-4">

                  {/* market_insight paragraph */}
                  {data.market_insight && (
                    <p className="text-[13px] leading-[1.75]" style={{ color: ink(2), ...sans }}>{data.market_insight}</p>
                  )}

                  {/* 3-column meta row */}
                  {(data.entry_barrier || data.salary_p50 || data.typical_employers?.length) && (
                    <div className="grid grid-cols-3 gap-3">
                      {data.entry_barrier && (
                        <div className="rounded-xl border px-3 py-2.5" style={{ background: 'var(--bg-paper)', borderColor: 'var(--line)' }}>
                          <p className="text-[10px] font-medium mb-1" style={{ color: ink(3), ...sans }}>入门门槛</p>
                          <p className="text-[13px] font-bold" style={{ color: ink(1), ...sans }}>
                            {data.entry_barrier === 'high' ? '高' : data.entry_barrier === 'medium' ? '中' : '低'}
                          </p>
                        </div>
                      )}
                      {data.salary_p50 && (
                        <div className="rounded-xl border px-3 py-2.5" style={{ background: 'var(--bg-paper)', borderColor: 'var(--line)' }}>
                          <p className="text-[10px] font-medium mb-1" style={{ color: ink(3), ...sans }}>月薪中位数</p>
                          <p className="text-[13px] font-bold" style={{ color: ink(1), ...sans }}>{(data.salary_p50 / 1000).toFixed(0)}k</p>
                        </div>
                      )}
                      {data.typical_employers && data.typical_employers.length > 0 && (
                        <div className="rounded-xl border px-3 py-2.5 col-span-1" style={{ background: 'var(--bg-paper)', borderColor: 'var(--line)' }}>
                          <p className="text-[10px] font-medium mb-1" style={{ color: ink(3), ...sans }}>典型雇主</p>
                          <p className="text-[11px] leading-snug" style={{ color: ink(2), ...sans }}>
                            {data.typical_employers.slice(0, 4).join(' · ')}
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* career_ceiling + ai_impact_narrative 统一卡片 */}
                  {data.career_ceiling && (
                    <div className="rounded-xl border px-4 py-3" style={{ background: 'var(--bg-paper)', borderColor: 'var(--line)' }}>
                      <p className="text-[10px] font-bold uppercase tracking-wider mb-1.5" style={{ color: ink(3), ...sans }}>发展天花板</p>
                      <p className="text-[12px] leading-[1.7]" style={{ color: ink(2), ...sans }}>{data.career_ceiling}</p>
                    </div>
                  )}
                  {data.ai_impact_narrative && (
                    <div className="rounded-xl border px-4 py-3" style={{ background: 'var(--bg-paper)', borderColor: 'var(--line)' }}>
                      <p className="text-[10px] font-bold uppercase tracking-wider mb-1.5" style={{ color: ink(3), ...sans }}>AI 影响分析</p>
                      <p className="text-[12px] leading-[1.7]" style={{ color: ink(2), ...sans }}>{data.ai_impact_narrative}</p>
                    </div>
                  )}

                </div>
              </div>
            </>
          )}

          {data.contextual_narrative && (
            <>
              <div className="border-t" style={{ borderColor: 'var(--line)' }} />
              <div className="px-5 py-4">
                <h3 className="text-[14px] font-bold mb-4" style={{ color: ink(1), ...sans }}>这个方向真实的样子</h3>
                <div className="space-y-3">
                  {NARRATIVE_FIELDS.map(({ key, label }) => {
                    const content = (data.contextual_narrative as Record<string, string>)?.[key]
                    if (!content) return null
                    return (
                      <div key={key} className="rounded-xl border px-4 py-3" style={{ background: 'var(--bg-paper)', borderColor: 'var(--line)' }}>
                        <p className="text-[10px] font-bold uppercase tracking-wider mb-1.5" style={{ color: ink(3), ...sans }}>{label}</p>
                        <p className="text-[12px] leading-[1.7]" style={{ color: ink(2), ...sans }}>{content}</p>
                      </div>
                    )
                  })}
                </div>
              </div>

              <div className="border-t" style={{ borderColor: 'var(--line)' }} />
              <div className="text-center py-2">
                <Link
                  to={`/explore?left=${data.node_id}`}
                  className="text-[13px] font-semibold border-b-2 pb-0.5 transition-colors hover:opacity-70"
                  style={{ color: ink(1), borderColor: ink(1), ...sans }}
                >
                  对比相似方向 →
                </Link>
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
                className="w-full py-3 rounded-xl text-[14px] font-semibold text-white cursor-pointer hover:opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ background: '#6B3E2E', ...sans }}
              >
                {confirming ? '设定中...' : `开始探索「${data.label}」方向`}
              </button>
              <button
                onClick={() => navigate(`/interview?role=${encodeURIComponent(data.label)}`)}
                className="w-full mt-2 py-2.5 rounded-xl border text-[13px] font-medium cursor-pointer transition-all flex items-center justify-center gap-2"
                style={{ borderColor: 'var(--line)', color: ink(2), background: 'var(--bg-card)', ...sans }}
              >
                <MessageSquare className="w-4 h-4" />
                针对「{data.label}」模拟面试
              </button>
              <p className="text-[11px] text-center mt-2" style={{ color: ink(3), ...sans }}>
                系统将追踪你与此方向的差距，随时可以更换
              </p>
            </>
          ) : (
            <>
              <button
                onClick={() => navigate('/profile?from=goal-set')}
                className="w-full py-3 rounded-xl text-[14px] font-semibold cursor-pointer hover:opacity-90 transition-all border"
                style={{ background: 'var(--bg-paper)', borderColor: 'var(--line)', color: ink(2), ...sans }}
              >
                先建立画像，再设定目标
              </button>
              <p className="text-[11px] text-center mt-2" style={{ color: ink(3), ...sans }}>
                上传简历后才能计算你与此方向的真实差距
              </p>
            </>
          )}
        </div>
      )}

      {/* ── Goal Confirmation Modal ── */}
      {showGoalConfirm && data && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-6 animate-fade-in"
          style={{ animationDuration: '0.18s' }}
          onClick={() => { if (!confirming) setShowGoalConfirm(false) }}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-[#3D2B1F]/40 backdrop-blur-md" />

          {/* Card */}
          <div
            className="relative max-w-[440px] w-full rounded-[24px] shadow-2xl p-7 space-y-5 animate-slide-up"
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--line)',
              boxShadow: '0 8px 40px rgba(0,0,0,0.14)',
              animationDuration: '0.3s',
            }}
            onClick={e => e.stopPropagation()}
          >
              {/* Close button */}
              <button
                onClick={() => { if (!confirming) setShowGoalConfirm(false) }}
                className="absolute top-5 right-5 w-8 h-8 rounded-full flex items-center justify-center transition-all cursor-pointer"
                style={{ background: 'var(--bg-paper)', color: ink(3) }}
              >
                <X className="w-4 h-4" />
              </button>

              {/* Header */}
              <div className="pr-8">
                <h3 className="text-[18px] font-extrabold" style={{ color: ink(1), ...sans }}>确认设定职业方向</h3>
                <p className="text-[12px] mt-1" style={{ color: ink(3), ...sans }}>在此之前，请确认你理解这意味着什么</p>
              </div>

              {/* Direction badge */}
              <div className="rounded-2xl px-4 py-3.5 flex items-center gap-3" style={{ background: '#FDF5E8', border: '1px solid #EBDDD0' }}>
                <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0" style={{ background: 'rgba(184, 92, 56, 0.12)' }}>
                  <Check className="w-4.5 h-4.5" style={{ color: '#B85C38' }} strokeWidth={2.5} />
                </div>
                <div>
                  <p className="text-[14px] font-extrabold" style={{ color: ink(1), ...sans }}>{data.label}</p>
                  <p className="text-[11px] mt-0.5" style={{ color: ink(3), ...sans }}>你选定的成长方向</p>
                </div>
              </div>

              {/* What this means */}
              <div className="space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: ink(3), ...sans }}>设定后，系统会</p>
                {[
                  { Icon: Briefcase,     text: '优先为你推送这个方向的真实 JD 做诊断' },
                  { Icon: BarChart2,     text: 'Coach 持续追踪你与这个方向的技能差距' },
                  { Icon: ClipboardList, text: '成长档案按此目标记录你的项目和求职进展' },
                ].map(({ Icon, text }, i) => (
                  <div key={i} className="flex items-center gap-3 rounded-xl px-3.5 py-2.5 border" style={{ background: 'var(--bg-paper)', borderColor: 'var(--line)' }}>
                    <div className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0" style={{ background: 'rgba(184, 92, 56, 0.08)' }}>
                      <Icon className="w-4 h-4" style={{ color: '#B85C38' }} strokeWidth={1.8} />
                    </div>
                    <p className="text-[12.5px] leading-relaxed" style={{ color: ink(2), ...sans }}>{text}</p>
                  </div>
                ))}
              </div>

              {/* Reassurance */}
              <p className="text-[11px] text-center" style={{ color: ink(3), ...sans }}>
                方向可以随时更换，不会丢失已有的记录和诊断数据
              </p>

              {/* Actions */}
              <div className="flex gap-3">
                <button
                  onClick={() => setShowGoalConfirm(false)}
                  disabled={confirming}
                  className="flex-1 py-3 rounded-2xl text-[13px] font-semibold transition-all cursor-pointer disabled:opacity-50 border"
                  style={{ color: ink(2), background: 'var(--bg-paper)', borderColor: 'var(--line)', ...sans }}
                >
                  再想想
                </button>
                <button
                  onClick={handleConfirmGoal}
                  disabled={confirming}
                  className="flex-1 py-3 rounded-2xl text-[13px] font-bold text-white hover:opacity-90 transition-all cursor-pointer disabled:opacity-60"
                  style={{ background: '#6B3E2E', ...sans }}
                >
                  {confirming ? '设定中...' : '确认，开始追踪'}
                </button>
              </div>
          </div>
        </div>
      )}
    </div>
  )
}

/* ── Shared components ─────────────────────────────────────────────────── */

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="text-[11px] font-bold uppercase tracking-wider mb-2" style={{ color: ink(3), ...sans }}>{children}</h3>
}

function NavLink({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-1.5 text-[11px] transition-colors cursor-pointer"
      style={{ color: ink(2), ...sans }}
      onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--chestnut)')}
      onMouseLeave={(e) => (e.currentTarget.style.color = ink(2))}
    >
      <ArrowRight className="w-3 h-3" style={{ color: ink(3) }} />
      {label}
    </button>
  )
}

function MatchBar({ label, score, detail: _detail }: {
  label: string; score: number; detail: string
}) {
  const barColor = score >= 80 ? '#5A8F6E' : score >= 60 ? '#C4853F' : score >= 40 ? '#B85C38' : '#9CA3AF'
  return (
    <div className="flex items-center gap-3">
      <span className="text-[12px] w-14 shrink-0 font-medium" style={{ color: ink(2), ...sans }}>{label}</span>
      <div className="flex-1 h-[3px] rounded-full overflow-hidden" style={{ background: '#F0EBE5' }}>
        <div className="h-full rounded-full" style={{ width: `${score}%`, background: barColor }} />
      </div>
      <span className="text-[12px] font-semibold w-8 text-right tabular-nums" style={{ color: ink(1), ...sans }}>{score}</span>
    </div>
  )
}

function AiBar({ icon, label, value, low, high, invert }: {
  icon: React.ReactNode; label: string; value: number; low: string; high: string; invert?: boolean
}) {
  const pct = Math.min(Math.max(value, 0), 100)
  const barColor = invert
    ? (pct <= 30 ? '#5A8F6E' : pct <= 60 ? '#C4853F' : '#B85C38')
    : (pct >= 70 ? '#5A8F6E' : pct >= 40 ? '#C4853F' : '#B85C38')
  const levelText = invert
    ? (pct <= 30 ? low : pct <= 60 ? '中' : high)
    : (pct >= 70 ? high : pct >= 40 ? '中' : low)

  return (
    <div className="flex items-center gap-3">
      <span className="shrink-0" style={{ color: ink(3) }}>{icon}</span>
      <span className="text-[11px] w-14 shrink-0" style={{ color: ink(3), ...sans }}>{label}</span>
      <div className="flex-1 h-[2px] rounded-full overflow-hidden" style={{ background: '#F0EBE5' }}>
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: barColor }} />
      </div>
      <span className="text-[10px] font-semibold w-10 text-right tabular-nums" style={{ color: ink(2), ...sans }}>{pct}%</span>
      <span className="text-[10px] w-6 text-right" style={{ color: ink(3), ...sans }}>{levelText}</span>
    </div>
  )
}
