import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  ChevronLeft,
  User,
  Briefcase,
  TrendingUp,
  FileText,
  Sparkles,
  Target,
  Lightbulb,
  ArrowRight,
  Clock,
  Trash2,
  Percent,
  BarChart3,
  Search,
} from 'lucide-react'
import {
  getJDDiagnosis,
  listJDDiagnoses,
  diagnoseJd,
  type JDDiagnosisDetail,
} from '@/api/jd'
import { useAuth } from '@/hooks/useAuth'
import { useProfileData } from '@/hooks/useProfileData'
import { formatDateShort } from '@/utils/format'
import { CoachInsightCard } from '@/components/CoachInsightCard'
import Navbar from '@/components/shared/Navbar'

const ease = [0.23, 1, 0.32, 1] as const

/* ── Design Tokens ── */
const t = {
  bg: '#F9F4EE',
  ink: '#1F1F1F',
  inkSecondary: '#6B6560',
  inkMuted: '#9A9590',
  line: '#D9D4CC',
  cardLine: '#EDE8DF',
  accent: '#B85C38',
  button: '#6B3E2E',
  buttonHover: '#5A3426',
  iconBg: '#F5F0E8',
  cardBg: '#FFFFFF',
} as const

const serif = { fontFamily: 'var(--font-serif), Georgia, "Noto Serif SC", serif' }
const sans = { fontFamily: 'var(--font-sans), "Noto Sans SC", system-ui, sans-serif' }
const cardShadow = { boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02)' }

/* ── Score helpers ── */
function matchQualitative(score: number) {
  if (score >= 80)
    return {
      label: '高度匹配',
      desc: '核心技能基本覆盖，竞争力较强',
      color: 'text-emerald-700',
      bg: 'bg-emerald-50',
      border: 'border-emerald-200',
    }
  if (score >= 60)
    return {
      label: '基础匹配',
      desc: '具备基础能力，有若干可补强项',
      color: 'text-blue-700',
      bg: 'bg-blue-50',
      border: 'border-blue-200',
    }
  if (score >= 40)
    return {
      label: '需补强',
      desc: '有一定基础，但核心缺口较多',
      color: 'text-amber-700',
      bg: 'bg-amber-50',
      border: 'border-amber-200',
    }
  return {
    label: '差距较大',
    desc: '技能覆盖度低，建议先补基础',
    color: 'text-red-700',
    bg: 'bg-red-50',
    border: 'border-red-200',
  }
}

function dimLevel(s: number) {
  if (s >= 80) return { label: '强', color: 'text-emerald-700', bg: 'bg-emerald-50' }
  if (s >= 60) return { label: '中', color: 'text-blue-700', bg: 'bg-blue-50' }
  if (s >= 40) return { label: '弱', color: 'text-amber-700', bg: 'bg-amber-50' }
  return { label: '缺', color: 'text-red-700', bg: 'bg-red-50' }
}

const ZONE_KEYS = ['leverage', 'transition', 'caution', 'critical'] as const
type ZoneKey = (typeof ZONE_KEYS)[number]

const zoneMap: Record<ZoneKey, { label: string; color: string; bg: string; desc: string }> = {
  leverage: { label: '协同优势区', color: 'text-emerald-700', bg: 'bg-emerald-50', desc: 'AI 增强人，人+AI 协同效应最强' },
  transition: { label: '转型过渡区', color: 'text-blue-700', bg: 'bg-blue-50', desc: '部分任务自动化，需要主动转型' },
  caution: { label: '替代警惕区', color: 'text-amber-700', bg: 'bg-amber-50', desc: 'AI 替代压力较高，建议提前准备' },
  critical: { label: '关键防御区', color: 'text-red-700', bg: 'bg-red-50', desc: 'AI 难以替代，但需持续深耕' },
}

function isZoneKey(z: string): z is ZoneKey {
  return ZONE_KEYS.includes(z as ZoneKey)
}

const dimLabelMap: Record<string, string> = {
  foundation: '基础素养',
  skill: '技能匹配',
  potential: '成长潜力',
  soft_skill: '软技能',
}

const sampleJDs = [
  {
    label: 'Java 后端 · 3-5年',
    text: '负责核心业务系统的设计与开发，要求精通 Java/Spring Boot，熟悉 MySQL、Redis、Kafka，具备微服务架构和分布式系统设计经验，有大型互联网项目背景优先。',
  },
  {
    label: '产品经理 · 应届',
    text: '协助产品经理完成需求分析、竞品调研、用户访谈、原型设计和 PRD 撰写。要求具备良好的逻辑思维、沟通表达能力和数据分析意识，熟悉 Axure/Figma 优先。',
  },
  {
    label: '前端开发 · 1-3年',
    text: '负责公司 Web 和移动端前端开发，要求精通 React 或 Vue，熟悉 TypeScript、Webpack/Vite，了解前端工程化和性能优化，有小程序或跨端开发经验优先。',
  },
]

function skillName(item: string | { skill: string }): string {
  return typeof item === 'string' ? item : item.skill
}

/* ── Card Shell ── */
function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`bg-white/50 backdrop-blur-sm rounded-2xl border border-white/40 p-6 ${className}`}
    >
      {children}
    </div>
  )
}

/* ── Page ── */
export default function JDDiagnosisPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const diagnosisId = id ? parseInt(id, 10) : null

  const { data, isLoading, error } = useQuery({
    queryKey: ['jd-diagnosis', diagnosisId],
    queryFn: () => getJDDiagnosis(diagnosisId!),
    enabled: !!diagnosisId && !isNaN(diagnosisId),
    staleTime: 60_000,
  })

  if (!diagnosisId || isNaN(diagnosisId)) {
    return (
      <main className="min-h-screen pt-[64px]" style={{ background: t.bg, color: t.ink }}>
        <Navbar />
        <JDInputForm />
      </main>
    )
  }

  if (isLoading) {
    return (
      <main className="min-h-screen pt-[64px]" style={{ background: t.bg, color: t.ink }}>
        <Navbar />
        <div className="h-[60vh] flex items-center justify-center">
          <div className="flex items-center gap-3">
            <div className="w-5 h-5 border-2 border-[#6B3E2E] border-t-transparent rounded-full animate-spin" />
            <span className="text-[14px]" style={{ color: t.inkSecondary }}>加载诊断结果...</span>
          </div>
        </div>
      </main>
    )
  }

  if (error || !data) {
    return (
      <main className="min-h-screen pt-[64px]" style={{ background: t.bg, color: t.ink }}>
        <Navbar />
        <div className="h-[60vh] flex items-center justify-center">
          <div className="text-center">
            <p className="text-[14px] text-red-600 mb-3">加载失败</p>
            <button
              onClick={() => navigate(-1)}
              className="px-4 py-2 rounded-lg text-white text-[13px] font-medium cursor-pointer"
              style={{ background: t.button }}
            >
              返回
            </button>
          </div>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen pt-[64px]" style={{ background: t.bg, color: t.ink }}>
      <Navbar />
      <DiagnosisResult data={data} />
    </main>
  )
}

/* ── Input Form (参考图1布局) ── */
function JDInputForm() {
  const navigate = useNavigate()
  const [jdInput, setJdInput] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const { token } = useAuth()
  const { profile } = useProfileData(token)

  const { data: history } = useQuery({
    queryKey: ['jd-diagnosis-history'],
    queryFn: () => listJDDiagnoses(),
    staleTime: 60_000,
  })

  const handleSubmit = async () => {
    if (!jdInput.trim()) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const result = await diagnoseJd({ jd_text: jdInput })
      navigate(`/jd-diagnosis/${result.id}`, { replace: true })
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : '诊断失败')
    } finally {
      setSubmitting(false)
    }
  }

  const targetLabel =
    profile?.career_goals?.[0]?.target_label ??
    profile?.graph_position?.target_label
  const skillCount = profile?.profile?.skills?.length ?? 0
  const historyCount = history?.length ?? 0
  const hasProfile = !!targetLabel && skillCount > 0

  return (
    <div className="h-full w-full overflow-y-auto">
      <div className="max-w-[1440px] mx-auto px-6 md:px-12 py-8">
        {/* Header */}
        <div className="mb-8 relative">
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease }}
          >
            <button
              onClick={() => navigate(-1)}
              className="flex items-center gap-1 text-[13px] hover:text-[#1F1F1F] transition-colors mb-4"
              style={{ color: t.inkMuted }}
            >
              <ChevronLeft className="w-4 h-4" />
              返回首页
            </button>
            <h1
              className="text-[32px] font-normal tracking-tight mb-2"
              style={{ ...serif, color: t.ink }}
            >
              JD 诊断
            </h1>
            <p className="text-[14px]" style={{ ...sans, color: t.inkSecondary }}>
              粘贴招聘要求，分析你与岗位的匹配度和技能缺口
            </p>
          </motion.div>

          {/* Decorative illustration - top right */}
          <div className="hidden lg:flex absolute right-0 top-0 items-center justify-center w-48 h-28">
            <div className="relative opacity-30">
              <FileText className="w-16 h-16 text-[#D9D4CC]" strokeWidth={1} />
              <div className="absolute -bottom-1 -right-2 w-12 h-12 rounded-full border-2 border-[#D9D4CC] flex items-center justify-center bg-[#F9F4EE]">
                <Search className="w-6 h-6 text-[#D9D4CC]" strokeWidth={1.5} />
              </div>
            </div>
          </div>
        </div>

        {/* Current Profile - full width */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05, duration: 0.4, ease }}
          className="mb-6"
        >
          <Card>
            <div className="flex items-center justify-between gap-6 flex-wrap">
              <div className="flex items-center gap-4">
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center"
                  style={{ background: t.iconBg }}
                >
                  <User className="w-6 h-6" style={{ color: t.button }} />
                </div>
                <div>
                  <h2 className="text-[16px] font-semibold" style={{ color: t.ink, ...sans }}>
                    当前画像
                  </h2>
                  <p className="text-[12px] mt-0.5" style={{ color: t.inkMuted }}>
                    基于你的简历和目标方向
                  </p>
                </div>
              </div>

              {hasProfile ? (
                <div className="flex items-center gap-6 flex-wrap">
                  <div className="flex items-center gap-2">
                    <Briefcase className="w-4 h-4" style={{ color: t.inkMuted }} />
                    <span className="text-[12px]" style={{ color: t.inkMuted }}>
                      目标岗位
                    </span>
                    <span className="text-[14px] font-semibold" style={{ color: t.ink }}>
                      {targetLabel}
                    </span>
                  </div>
                  <div className="w-px h-8" style={{ background: t.line }} />
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4" style={{ color: t.inkMuted }} />
                    <span className="text-[12px]" style={{ color: t.inkMuted }}>
                      技能覆盖
                    </span>
                    <span className="text-[14px] font-semibold" style={{ color: t.ink }}>
                      {skillCount} 项
                    </span>
                  </div>
                  <div className="w-px h-8" style={{ background: t.line }} />
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4" style={{ color: t.inkMuted }} />
                    <span className="text-[12px]" style={{ color: t.inkMuted }}>
                      诊断记录
                    </span>
                    <span className="text-[14px] font-semibold" style={{ color: t.ink }}>
                      {historyCount} 次
                    </span>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-3">
                  <p className="text-[13px]" style={{ color: t.inkSecondary }}>
                    画像信息较空，诊断结果可能不够准确
                  </p>
                  <button
                    onClick={() => navigate('/profile')}
                    className="text-[13px] font-semibold cursor-pointer hover:underline"
                    style={{ color: t.button }}
                  >
                    去完善
                  </button>
                </div>
              )}
            </div>
          </Card>
        </motion.div>

        {/* Main Content Grid */}
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Left Column */}
          <div className="flex-[2] space-y-6">
            {/* JD Input Card */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1, duration: 0.4, ease }}
            >
              <Card>
                {/* Card Header */}
                <div className="flex items-center gap-3 mb-4">
                  <div
                    className="w-8 h-8 rounded-full flex items-center justify-center"
                    style={{ background: t.iconBg }}
                  >
                    <Target className="w-4 h-4" style={{ color: t.button }} />
                  </div>
                  <div>
                    <h2 className="text-[16px] font-semibold" style={{ color: t.ink, ...sans }}>
                      粘贴招聘要求
                    </h2>
                    <p className="text-[12px] mt-0.5" style={{ color: t.inkMuted }}>
                      从 JD 中复制职责要求、技能要求等内容，越完整诊断越准确
                    </p>
                  </div>
                </div>

                {/* Sample Tags */}
                <div className="flex flex-wrap gap-2 mb-4">
                  {sampleJDs.map((sample) => (
                    <button
                      key={sample.label}
                      onClick={() => setJdInput(sample.text)}
                      className="px-3 py-1.5 rounded-full text-[12px] transition-colors"
                      style={{
                        background: t.bg,
                        color: t.inkSecondary,
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = t.cardLine
                        e.currentTarget.style.color = t.ink
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = t.bg
                        e.currentTarget.style.color = t.inkSecondary
                      }}
                    >
                      {sample.label}
                    </button>
                  ))}
                  <button
                    className="px-3 py-1.5 rounded-full border border-dashed text-[12px] transition-colors"
                    style={{ borderColor: t.line, color: t.inkMuted }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = t.inkSecondary
                      e.currentTarget.style.color = t.inkSecondary
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = t.line
                      e.currentTarget.style.color = t.inkMuted
                    }}
                  >
                    + 自定义标签
                  </button>
                </div>

                {/* Textarea */}
                <div className="relative mb-4">
                  <textarea
                    value={jdInput}
                    onChange={(e) => setJdInput(e.target.value)}
                    placeholder="请将职位的招聘要求全文粘贴到这里..."
                    rows={8}
                    maxLength={5000}
                    className="w-full px-4 py-3 rounded-xl text-[14px] placeholder:text-[#9A9590] focus:outline-none resize-none leading-relaxed transition-all"
                    style={{
                      border: `1px solid ${t.line}`,
                      background: 'rgba(255,255,255,0.35)',
                      color: t.ink,
                    }}
                    onFocus={(e) => {
                      e.currentTarget.style.borderColor = t.button
                      e.currentTarget.style.boxShadow = `0 0 0 3px rgba(107,62,46,0.08)`
                    }}
                    onBlur={(e) => {
                      e.currentTarget.style.borderColor = t.line
                      e.currentTarget.style.boxShadow = 'none'
                    }}
                  />
                  <span
                    className="absolute bottom-3 right-3 text-[12px]"
                    style={{ color: t.inkMuted }}
                  >
                    {jdInput.length} / 5000
                  </span>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between flex-wrap gap-3">
                  <div className="flex items-center gap-1.5 text-[12px]" style={{ color: t.inkMuted }}>
                    <FileText className="w-3.5 h-3.5" />
                    <span>支持复制 JD 全文，或从招聘平台直接粘贴</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => setJdInput('')}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-[13px] transition-colors"
                      style={{
                        border: `1px solid ${t.line}`,
                        color: t.inkSecondary,
                        background: t.cardBg,
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor = t.inkSecondary
                        e.currentTarget.style.color = t.ink
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = t.line
                        e.currentTarget.style.color = t.inkSecondary
                      }}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      清空内容
                    </button>
                    <button
                      onClick={handleSubmit}
                      disabled={!jdInput.trim() || submitting}
                      className="flex items-center gap-1.5 px-5 py-2 rounded-lg text-[13px] font-medium text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                      style={{ background: t.button }}
                      onMouseEnter={(e) => {
                        if (!e.currentTarget.disabled) e.currentTarget.style.background = t.buttonHover
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = t.button
                      }}
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      {submitting ? '分析中...' : '开始诊断'}
                    </button>
                  </div>
                </div>

                {submitError && (
                  <div className="mt-3 px-3 py-2 rounded-lg bg-red-50 border border-red-100 text-[13px] text-red-600">
                    {submitError}
                  </div>
                )}
              </Card>
            </motion.div>

            {/* History Card */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15, duration: 0.4, ease }}
            >
              <Card>
                <div className="flex items-center gap-2 mb-4">
                  <Clock className="w-4 h-4" style={{ color: t.button }} />
                  <h2 className="text-[16px] font-semibold" style={{ color: t.ink, ...sans }}>
                    历史诊断
                  </h2>
                </div>

                {history && history.length > 0 ? (
                  <div className="space-y-1">
                    {history.slice(0, 5).map((item) => {
                      const q = matchQualitative(item.match_score)
                      return (
                        <button
                          key={item.id}
                          onClick={() => navigate(`/jd-diagnosis/${item.id}`)}
                          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left group transition-colors"
                          style={{ color: t.ink }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.background = t.bg
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.background = 'transparent'
                          }}
                        >
                          <span
                            className={`text-[12px] font-medium px-2.5 py-0.5 rounded-full shrink-0 ${q.bg} ${q.color}`}
                          >
                            {q.label}
                          </span>
                          <span className="flex-1 text-[13px] truncate" style={{ color: t.ink }}>
                            {item.jd_title}
                          </span>
                          <span className="text-[12px] shrink-0" style={{ color: t.inkMuted }}>
                            {formatDateShort(item.created_at)}
                          </span>
                          <ArrowRight
                            className="w-3.5 h-3.5 shrink-0 transition-all"
                            style={{ color: t.inkMuted }}
                          />
                        </button>
                      )
                    })}
                  </div>
                ) : (
                  <div className="py-10 flex flex-col items-center justify-center text-center">
                    <div
                      className="w-16 h-16 rounded-full flex items-center justify-center mb-3"
                      style={{ background: t.iconBg }}
                    >
                      <FileText className="w-8 h-8" style={{ color: t.line }} />
                    </div>
                    <p className="text-[14px] font-medium mb-1" style={{ color: t.inkSecondary }}>
                      还没有诊断记录
                    </p>
                    <p className="text-[12px]" style={{ color: t.inkMuted }}>
                      从上方粘贴第一份 JD 开始
                    </p>
                  </div>
                )}
              </Card>
            </motion.div>
          </div>

          {/* Right Column */}
          <div className="flex-1 space-y-6">
            {/* Features Card */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.12, duration: 0.4, ease }}
            >
              <Card>
                <div className="flex items-center gap-2 mb-5">
                  <Sparkles className="w-4 h-4" style={{ color: t.button }} />
                  <h2 className="text-[16px] font-semibold" style={{ color: t.ink, ...sans }}>
                    诊断将为你提供
                  </h2>
                </div>

                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <div
                      className="w-9 h-9 rounded-full flex items-center justify-center shrink-0"
                      style={{ background: t.iconBg }}
                    >
                      <Percent className="w-4 h-4" style={{ color: t.button }} />
                    </div>
                    <div>
                      <h3 className="text-[13px] font-semibold mb-0.5" style={{ color: t.ink }}>
                        匹配度分析
                      </h3>
                      <p className="text-[12px]" style={{ color: t.inkMuted }}>
                        综合评估你与岗位的匹配程度
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <div
                      className="w-9 h-9 rounded-full flex items-center justify-center shrink-0"
                      style={{ background: t.iconBg }}
                    >
                      <BarChart3 className="w-4 h-4" style={{ color: t.button }} />
                    </div>
                    <div>
                      <h3 className="text-[13px] font-semibold mb-0.5" style={{ color: t.ink }}>
                        技能差距
                      </h3>
                      <p className="text-[12px]" style={{ color: t.inkMuted }}>
                        明确你需要提升的关键技能
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <div
                      className="w-9 h-9 rounded-full flex items-center justify-center shrink-0"
                      style={{ background: t.iconBg }}
                    >
                      <Lightbulb className="w-4 h-4" style={{ color: t.button }} />
                    </div>
                    <div>
                      <h3 className="text-[13px] font-semibold mb-0.5" style={{ color: t.ink }}>
                        提升建议
                      </h3>
                      <p className="text-[12px]" style={{ color: t.inkMuted }}>
                        给出个性化的学习和成长建议
                      </p>
                    </div>
                  </div>
                </div>
              </Card>
            </motion.div>

            {/* Tips Card */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.18, duration: 0.4, ease }}
            >
              <Card>
                <div className="flex items-center gap-2 mb-3">
                  <Lightbulb className="w-4 h-4" style={{ color: t.button }} />
                  <h2 className="text-[14px] font-semibold" style={{ color: t.ink, ...sans }}>
                    小贴士
                  </h2>
                </div>
                <p className="text-[12px] leading-relaxed" style={{ color: t.inkSecondary }}>
                  粘贴完整的职位描述（包括职责和要求），能获得更精准的分析结果
                </p>
              </Card>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  )
}

/* ── Result Page ── */
function DiagnosisResult({ data }: { data: JDDiagnosisDetail }) {
  const navigate = useNavigate()
  const score = data.match_score ?? 0
  const matched = data.matched_skills ?? []
  const gaps = data.gap_skills ?? []
  const dimensions = data.dimensions ?? {}
  const tips = data.resume_tips ?? []
  const graphContext = data.graph_context

  const matchedCount = matched.length
  const gapsCount = gaps.length
  const qual = matchQualitative(score)

  const zoneCfg = graphContext?.zone && isZoneKey(graphContext.zone)
    ? zoneMap[graphContext.zone]
    : null

  return (
    <div className="h-full w-full overflow-y-auto">
      <div className="max-w-[1440px] mx-auto px-6 md:px-12 py-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease }}
          className="mb-6"
        >
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-1 text-[13px] hover:text-[#1F1F1F] transition-colors mb-4"
            style={{ color: t.inkMuted }}
          >
            <ChevronLeft className="w-4 h-4" />
            返回
          </button>
          <h1 className="text-[28px] font-normal tracking-tight" style={{ ...serif, color: t.ink }}>
            {data.jd_title}
          </h1>
          <p className="text-[13px] mt-1" style={{ color: t.inkMuted }}>
            诊断于 {formatDateShort(data.created_at)}
          </p>
        </motion.div>

        <div className="flex flex-col lg:flex-row gap-6">
          {/* Left Column - Main Results */}
          <div className="flex-[2] space-y-6">
            {/* Score Overview */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05, duration: 0.4, ease }}
            >
              <Card>
                <div className="flex items-start gap-6">
                  <div className="flex flex-col items-center justify-center py-2 px-4 rounded-xl" style={{ background: t.iconBg }}>
                    <span className="text-[32px] font-normal leading-none" style={{ ...serif, color: t.button }}>
                      {score}
                    </span>
                    <span className="text-[11px] mt-1" style={{ color: t.inkMuted }}>匹配分</span>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`text-[13px] font-semibold px-2.5 py-0.5 rounded-full ${qual.bg} ${qual.color}`}>
                        {qual.label}
                      </span>
                    </div>
                    <p className="text-[13px] leading-relaxed" style={{ color: t.inkSecondary }}>
                      {qual.desc}。已具备 <span className="font-semibold" style={{ color: t.ink }}>{matchedCount}</span> 项核心技能
                      {gapsCount > 0 && (
                        <>
                          ，缺口 <span className="font-semibold" style={{ color: t.accent }}>{gapsCount}</span> 项
                        </>
                      )}
                      。
                    </p>
                  </div>
                </div>
              </Card>
            </motion.div>

            {/* AI Impact */}
            {graphContext && zoneCfg && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1, duration: 0.4, ease }}
              >
                <Card>
                  <h2 className="text-[16px] font-semibold mb-3" style={{ color: t.ink, ...sans }}>
                    AI 影响分析
                  </h2>
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`inline-block px-2.5 py-0.5 rounded-full text-[12px] font-medium ${zoneCfg.bg} ${zoneCfg.color}`}>
                      {zoneCfg.label}
                    </span>
                    <span className="text-[12px]" style={{ color: t.inkMuted }}>
                      图谱定位：{graphContext.label}
                    </span>
                  </div>
                  <p className="text-[13px] mb-3" style={{ color: t.inkSecondary }}>
                    {zoneCfg.desc}
                  </p>
                  <div className="flex items-center gap-4 text-[12px]" style={{ color: t.inkSecondary }}>
                    <span>
                      替代压力 <span className="font-semibold" style={{ color: t.ink }}>{graphContext.replacement_pressure}</span>/100
                    </span>
                    <span style={{ color: t.line }}>|</span>
                    <span>
                      人+AI 协同 <span className="font-semibold" style={{ color: t.ink }}>{graphContext.human_ai_leverage}</span>/100
                    </span>
                  </div>
                </Card>
              </motion.div>
            )}

            {/* Dimensions */}
            {Object.keys(dimensions).length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15, duration: 0.4, ease }}
              >
                <Card>
                  <h2 className="text-[16px] font-semibold mb-4" style={{ color: t.ink, ...sans }}>
                    四维评估
                  </h2>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    {Object.entries(dimensions).map(([key, dim]) => {
                      const lvl = dimLevel(dim.score ?? 0)
                      return (
                        <div key={key} className="text-center py-3 rounded-xl" style={{ background: t.bg }}>
                          <p className="text-[12px] mb-1" style={{ color: t.inkMuted }}>
                            {dimLabelMap[key] || key}
                          </p>
                          <p className="text-[20px] font-normal" style={{ ...serif, color: t.ink }}>
                            {dim.score ?? 0}
                          </p>
                          <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${lvl.bg} ${lvl.color}`}>
                            {lvl.label}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                </Card>
              </motion.div>
            )}

            {/* Skills */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              {matched.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2, duration: 0.4, ease }}
                >
                  <Card>
                    <h2 className="text-[14px] font-semibold mb-3" style={{ color: t.ink, ...sans }}>
                      已匹配技能（{matched.length}）
                    </h2>
                    <div className="flex flex-wrap gap-2">
                      {matched.map((m) => (
                        <span
                          key={skillName(m)}
                          className="px-2.5 py-1 rounded-full text-[12px] font-medium"
                          style={{ background: t.bg, color: t.inkSecondary }}
                        >
                          {skillName(m)}
                        </span>
                      ))}
                    </div>
                  </Card>
                </motion.div>
              )}

              {gaps.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.25, duration: 0.4, ease }}
                >
                  <Card>
                    <h2 className="text-[14px] font-semibold mb-3" style={{ color: t.ink, ...sans }}>
                      技能缺口（{gaps.length}）
                    </h2>
                    <div className="flex flex-wrap gap-2">
                      {gaps.map((g) => {
                        const isHigh =
                          typeof g === 'object' &&
                          g !== null &&
                          'priority' in g &&
                          g.priority === 'high'
                        return (
                          <span
                            key={skillName(g)}
                            className="px-2.5 py-1 rounded-full text-[12px] font-medium"
                            style={{
                              background: isHigh ? '#FEF2F2' : t.bg,
                              color: isHigh ? '#B91C1C' : t.inkSecondary,
                            }}
                          >
                            {skillName(g)}
                          </span>
                        )
                      })}
                    </div>
                  </Card>
                </motion.div>
              )}
            </div>

            {/* Escape Routes */}
            {graphContext?.escape_routes && graphContext.escape_routes.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3, duration: 0.4, ease }}
              >
                <Card>
                  <h2 className="text-[16px] font-semibold mb-4" style={{ color: t.ink, ...sans }}>
                    推荐转岗路线
                  </h2>
                  <div className="space-y-0">
                    {graphContext.escape_routes.map((route, idx) => {
                      const routeZone = isZoneKey(route.target_zone)
                        ? zoneMap[route.target_zone]
                        : null
                      const isLast = idx === graphContext.escape_routes!.length - 1
                      return (
                        <div
                          key={idx}
                          className="py-3"
                          style={{
                            borderBottom: isLast ? 'none' : `1px solid ${t.cardLine}`,
                          }}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 flex-wrap mb-1.5">
                                <span className="text-[13px] font-semibold" style={{ color: t.ink }}>
                                  {route.target_label}
                                </span>
                                {routeZone && (
                                  <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${routeZone.bg} ${routeZone.color}`}>
                                    {routeZone.label}
                                  </span>
                                )}
                                {route.tag && (
                                  <span className="text-[12px]" style={{ color: t.inkMuted }}>
                                    {route.tag}
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-1.5 flex-wrap">
                                <span className="text-[12px]" style={{ color: t.inkMuted }}>
                                  需补：
                                </span>
                                {route.gap_skills.slice(0, 3).map((skill, sIdx) => (
                                  <span
                                    key={sIdx}
                                    className="px-2 py-0.5 rounded-full text-[11px]"
                                    style={{
                                      background: t.bg,
                                      color: t.inkSecondary,
                                    }}
                                  >
                                    {skill}
                                  </span>
                                ))}
                              </div>
                            </div>
                            <span className="text-[12px] shrink-0 mt-0.5" style={{ color: t.inkMuted }}>
                              预估 {route.estimated_hours} 小时
                            </span>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </Card>
              </motion.div>
            )}

            {/* Resume Tips */}
            {tips.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35, duration: 0.4, ease }}
              >
                <Card>
                  <h2 className="text-[16px] font-semibold mb-4" style={{ color: t.ink, ...sans }}>
                    简历优化建议
                  </h2>
                  <ul className="space-y-3">
                    {tips.map((tip, i) => (
                      <li key={i} className="flex items-start gap-3">
                        <span
                          className="text-[12px] font-medium shrink-0 mt-0.5 w-5 h-5 rounded-full flex items-center justify-center"
                          style={{ background: t.iconBg, color: t.button }}
                        >
                          {i + 1}
                        </span>
                        <span className="text-[13px] leading-relaxed" style={{ color: t.inkSecondary }}>
                          {tip}
                        </span>
                      </li>
                    ))}
                  </ul>
                </Card>
              </motion.div>
            )}

            {data.coach_insight && (
              <CoachInsightCard insight={data.coach_insight} delay={0.38} />
            )}

            {/* Interview CTA */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.4, ease }}
            >
              <Card>
                <div className="flex items-center justify-between flex-wrap gap-4">
                  <div>
                    <p className="text-[14px] font-semibold mb-0.5" style={{ color: t.ink }}>
                      针对这份 JD 模拟面试
                    </p>
                    <p className="text-[12px]" style={{ color: t.inkMuted }}>
                      重点考察 {gapsCount} 项技能缺口
                    </p>
                  </div>
                  <button
                    onClick={() =>
                      navigate(
                        `/interview?role=${encodeURIComponent(data.jd_title)}&jd=${encodeURIComponent(data.jd_text.slice(0, 200))}`,
                      )
                    }
                    className="px-5 py-2.5 rounded-lg text-white text-[13px] font-medium cursor-pointer transition-colors"
                    style={{ background: t.button }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = t.buttonHover }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = t.button }}
                  >
                    开始面试
                  </button>
                </div>
              </Card>
            </motion.div>
          </div>

          {/* Right Column - Result Sidebar */}
          <div className="flex-1 space-y-6">
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15, duration: 0.4, ease }}
            >
              <Card>
                <h2 className="text-[16px] font-semibold mb-4" style={{ color: t.ink, ...sans }}>
                  诊断概览
                </h2>
                <div className="space-y-4">
                  <div className="flex items-center justify-between py-2" style={{ borderBottom: `1px solid ${t.cardLine}` }}>
                    <span className="text-[13px]" style={{ color: t.inkSecondary }}>匹配得分</span>
                    <span className="text-[18px] font-normal" style={{ ...serif, color: t.button }}>{score}</span>
                  </div>
                  <div className="flex items-center justify-between py-2" style={{ borderBottom: `1px solid ${t.cardLine}` }}>
                    <span className="text-[13px]" style={{ color: t.inkSecondary }}>已匹配技能</span>
                    <span className="text-[14px] font-semibold" style={{ color: t.ink }}>{matchedCount} 项</span>
                  </div>
                  <div className="flex items-center justify-between py-2" style={{ borderBottom: `1px solid ${t.cardLine}` }}>
                    <span className="text-[13px]" style={{ color: t.inkSecondary }}>技能缺口</span>
                    <span className="text-[14px] font-semibold" style={{ color: t.accent }}>{gapsCount} 项</span>
                  </div>
                  <div className="flex items-center justify-between py-2">
                    <span className="text-[13px]" style={{ color: t.inkSecondary }}>评估维度</span>
                    <span className="text-[14px] font-semibold" style={{ color: t.ink }}>{Object.keys(dimensions).length} 项</span>
                  </div>
                </div>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, duration: 0.4, ease }}
            >
              <Card>
                <div className="flex items-center gap-2 mb-3">
                  <Lightbulb className="w-4 h-4" style={{ color: t.button }} />
                  <h2 className="text-[14px] font-semibold" style={{ color: t.ink, ...sans }}>
                    小贴士
                  </h2>
                </div>
                <p className="text-[12px] leading-relaxed" style={{ color: t.inkSecondary }}>
                  针对技能缺口进行重点准备，可以显著提升面试通过率。建议优先补足标记为“高优先级”的技能项。
                </p>
              </Card>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  )
}
