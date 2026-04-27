import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  ChevronLeft,
  ArrowRight,
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

const ease = [0.22, 1, 0.36, 1] as const

/* ── Design Tokens (严格对齐首页) ── */
const t = {
  bg: '#F8F3ED',
  bgCard: 'rgba(255, 252, 249, 0.3)',
  ink: '#222222',
  inkSecondary: '#7A6F68',
  inkMuted: '#A69E96',
  line: '#E4D8CF',
  accent: '#C46A4A',
  accentSoft: '#E8C2AE',
  button: '#7A3E2E',
  buttonHover: '#6A2E1E',
} as const

const serif = { fontFamily: 'var(--font-serif), "Noto Serif SC", Georgia, serif' }
const sans = { fontFamily: 'var(--font-sans), "Noto Sans SC", "PingFang SC", system-ui, sans-serif' }

/* ── Score helpers ── */
function matchQualitative(score: number) {
  if (score >= 80) return { label: '高度匹配', desc: '核心技能基本覆盖，竞争力较强' }
  if (score >= 60) return { label: '基础匹配', desc: '具备基础能力，有若干可补强项' }
  if (score >= 40) return { label: '需补强', desc: '有一定基础，但核心缺口较多' }
  return { label: '差距较大', desc: '技能覆盖度低，建议先补基础' }
}

function dimLevel(s: number) {
  if (s >= 80) return { label: '强', color: t.button }
  if (s >= 60) return { label: '中', color: t.inkSecondary }
  if (s >= 40) return { label: '弱', color: t.inkMuted }
  return { label: '缺', color: t.accent }
}

const ZONE_KEYS = ['leverage', 'transition', 'caution', 'critical'] as const
type ZoneKey = (typeof ZONE_KEYS)[number]

const zoneMap: Record<ZoneKey, { label: string; color: string; desc: string }> = {
  leverage: { label: '协同优势区', color: t.button, desc: 'AI 增强人，人+AI 协同效应最强' },
  transition: { label: '转型过渡区', color: t.inkSecondary, desc: '部分任务自动化，需要主动转型' },
  caution: { label: '替代警惕区', color: t.accent, desc: 'AI 替代压力较高，建议提前准备' },
  critical: { label: '关键防御区', color: '#C44A3A', desc: 'AI 难以替代，但需持续深耕' },
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
      className={`rounded-2xl p-6 backdrop-blur-md ${className}`}
      style={{
        background: t.bgCard,
        border: '1px solid rgba(228, 216, 207, 0.5)',
        boxShadow: '0 1px 3px rgba(122, 62, 46, 0.04)',
      }}
    >
      {children}
    </div>
  )
}

/* ── Divider ── */
function Divider({ className = '' }: { className?: string }) {
  return <div className={`h-px w-full ${className}`} style={{ background: t.line }} />
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
            <div
              className="w-5 h-5 border-2 rounded-full animate-spin"
              style={{ borderColor: t.accent, borderTopColor: 'transparent' }}
            />
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
          <Card className="text-center">
            <p className="text-[14px] mb-4" style={{ color: t.accent }}>加载失败</p>
            <button
              onClick={() => navigate(-1)}
              className="px-5 py-2 rounded-lg text-white text-[13px] font-medium cursor-pointer transition-colors"
              style={{ background: t.button }}
              onMouseEnter={(e) => { e.currentTarget.style.background = t.buttonHover }}
              onMouseLeave={(e) => { e.currentTarget.style.background = t.button }}
            >
              返回
            </button>
          </Card>
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

/* ── Input Form ── */
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
      <div className="max-w-[1440px] mx-auto px-6 md:px-12">
        {/* Hero 区 */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, ease }}
          className="pt-16 pb-12 relative"
        >
          {/* 装饰光晕 */}
          <div
            className="absolute right-0 top-0 w-80 h-80 pointer-events-none"
            style={{
              background: `radial-gradient(ellipse at 70% 30%, ${t.accentSoft} 0%, transparent 60%)`,
              opacity: 0.3,
            }}
          />

          {/* 装饰线稿 */}
          <div className="absolute right-12 top-16 hidden lg:block pointer-events-none opacity-20">
            <svg width="160" height="160" viewBox="0 0 160 160" fill="none">
              <rect x="30" y="20" width="80" height="100" rx="4" stroke={t.inkSecondary} strokeWidth="1.5" />
              <line x1="45" y1="40" x2="95" y2="40" stroke={t.inkSecondary} strokeWidth="1" />
              <line x1="45" y1="52" x2="95" y2="52" stroke={t.inkSecondary} strokeWidth="1" />
              <line x1="45" y1="64" x2="80" y2="64" stroke={t.inkSecondary} strokeWidth="1" />
              <circle cx="115" cy="95" r="20" stroke={t.inkSecondary} strokeWidth="1.5" />
              <line x1="129" y1="109" x2="145" y2="125" stroke={t.inkSecondary} strokeWidth="1.5" />
            </svg>
          </div>

          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-1 text-[13px] hover:opacity-70 transition-opacity mb-8 cursor-pointer"
            style={{ color: t.inkMuted }}
          >
            <ChevronLeft className="w-4 h-4" />
            返回
          </button>

          <h1
            className="font-normal leading-[1.15] tracking-tight relative z-10"
            style={{
              ...serif,
              color: t.ink,
              fontSize: 'clamp(36px, 5vw, 52px)',
              maxWidth: '500px',
            }}
          >
            JD 诊断
          </h1>

          <p
            className="mt-6 leading-[1.8] relative z-10"
            style={{
              ...sans,
              color: t.inkSecondary,
              fontSize: '15px',
              maxWidth: '420px',
            }}
          >
            粘贴招聘要求，分析你与岗位的匹配度和技能缺口
          </p>
        </motion.div>

        {/* 当前画像卡片 */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.6, ease }}
          className="mb-8"
        >
          <Card>
            <div className="flex items-center gap-6 flex-wrap">
              <div>
                <p className="text-[12px]" style={{ color: t.inkMuted, ...sans }}>当前画像</p>
                <p className="text-[14px] font-medium" style={{ color: t.ink, ...sans }}>基于你的简历和目标方向</p>
              </div>

              <div className="h-8 w-px" style={{ background: t.line }} />

              {hasProfile ? (
                <>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[13px]" style={{ color: t.inkSecondary }}>目标</span>
                    <span
                      className="text-[13px] px-2.5 py-0.5 rounded-full font-medium"
                      style={{ background: t.accentSoft, color: t.button }}
                    >
                      {targetLabel}
                    </span>
                  </div>
                  <div className="h-8 w-px" style={{ background: t.line }} />
                  <div className="flex items-center gap-1.5">
                    <span className="text-[13px]" style={{ color: t.inkSecondary }}>技能</span>
                    <span className="text-[14px] font-medium" style={{ color: t.ink }}>{skillCount} 项</span>
                  </div>
                  <div className="h-8 w-px" style={{ background: t.line }} />
                  <div className="flex items-center gap-1.5">
                    <span className="text-[13px]" style={{ color: t.inkSecondary }}>历史</span>
                    <span className="text-[14px] font-medium" style={{ color: t.ink }}>{historyCount} 次</span>
                  </div>
                </>
              ) : (
                <div className="flex items-center gap-3">
                  <span className="text-[13px]" style={{ color: t.inkSecondary }}>画像信息较空，诊断结果可能不够准确</span>
                  <button
                    onClick={() => navigate('/profile')}
                    className="text-[13px] font-medium cursor-pointer hover:underline"
                    style={{ color: t.accent }}
                  >
                    去完善
                  </button>
                </div>
              )}
            </div>
          </Card>
        </motion.div>

        {/* 两栏布局 */}
        <div className="flex flex-col lg:flex-row gap-8 mb-12">
          {/* 左侧 - 输入卡片 (65%) */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.6, ease }}
            className="flex-[65]"
          >
            <Card className="h-full">
              <div className="mb-6">
                <h2 className="text-[18px] font-medium" style={{ color: t.ink, ...sans }}>粘贴招聘要求</h2>
                <p className="text-[12px] mt-1" style={{ color: t.inkMuted }}>从 JD 中复制职责要求、技能要求等内容，越完整诊断越准确</p>
              </div>

              {/* 示例标签 */}
              <div className="flex flex-wrap gap-2 mb-5">
                {sampleJDs.map((sample) => (
                  <button
                    key={sample.label}
                    onClick={() => setJdInput(sample.text)}
                    className="text-[13px] px-3.5 py-1.5 rounded-full cursor-pointer transition-colors"
                    style={{
                      background: t.bg,
                      color: t.inkSecondary,
                      border: `1px solid ${t.line}`,
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = t.accentSoft
                      e.currentTarget.style.color = t.button
                      e.currentTarget.style.borderColor = t.accentSoft
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = t.bg
                      e.currentTarget.style.color = t.inkSecondary
                      e.currentTarget.style.borderColor = t.line
                    }}
                  >
                    {sample.label}
                  </button>
                ))}
              </div>

              {/* Textarea */}
              <div className="relative mb-4">
                <textarea
                  value={jdInput}
                  onChange={(e) => setJdInput(e.target.value)}
                  placeholder="请将职位的招聘要求全文粘贴到这里..."
                  maxLength={5000}
                  className="w-full text-[15px] placeholder:opacity-40 focus:outline-none resize-none leading-[1.8] transition-all rounded-xl p-4"
                  style={{
                    background: t.bg,
                    color: t.ink,
                    border: `1px solid ${t.line}`,
                    height: '260px',
                    ...sans,
                  }}
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = t.accent
                    e.currentTarget.style.boxShadow = `0 0 0 3px ${t.accentSoft}`
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = t.line
                    e.currentTarget.style.boxShadow = 'none'
                  }}
                />
              </div>

              {/* 底部操作栏 */}
              <div className="flex items-center justify-between">
                <span className="text-[12px]" style={{ color: t.inkMuted }}>
                  支持复制 JD 全文，或从招聘平台直接粘贴
                </span>
                <div className="flex items-center gap-4">
                  <span className="text-[12px]" style={{ color: t.inkMuted }}>{jdInput.length} / 5000</span>
                  <button
                    onClick={() => setJdInput('')}
                    className="text-[13px] cursor-pointer hover:opacity-70 transition-opacity"
                    style={{ color: t.inkMuted }}
                  >
                    清空
                  </button>
                  <button
                    onClick={handleSubmit}
                    disabled={!jdInput.trim() || submitting}
                    className="px-6 py-2.5 rounded-lg text-white text-[13px] font-medium cursor-pointer transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                    style={{ background: t.button }}
                    onMouseEnter={(e) => {
                      if (!e.currentTarget.disabled) {
                        e.currentTarget.style.background = t.buttonHover
                        e.currentTarget.style.transform = 'translateY(-1px)'
                      }
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = t.button
                      e.currentTarget.style.transform = 'translateY(0)'
                    }}
                  >
                    {submitting ? '分析中...' : '开始诊断'}
                  </button>
                </div>
              </div>

              {submitError && (
                <p className="mt-4 text-[13px]" style={{ color: t.accent }}>{submitError}</p>
              )}
            </Card>
          </motion.div>

          {/* 右侧 - 说明卡片 (35%) */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.6, ease }}
            className="flex-[35]"
          >
            <div className="space-y-6">
              <Card>
              <h2 className="text-[18px] font-medium mb-5" style={{ color: t.ink, ...sans }}>诊断将为你提供</h2>

              <div className="space-y-5">
                <div>
                  <h3 className="text-[14px] font-medium mb-0.5" style={{ color: t.ink, ...sans }}>01  匹配度分析</h3>
                  <p className="text-[13px] leading-relaxed" style={{ color: t.inkSecondary }}>综合评估你与岗位的匹配程度</p>
                </div>

                <Divider />

                <div>
                  <h3 className="text-[14px] font-medium mb-0.5" style={{ color: t.ink, ...sans }}>02  技能差距</h3>
                  <p className="text-[13px] leading-relaxed" style={{ color: t.inkSecondary }}>明确你需要提升的关键技能</p>
                </div>

                <Divider />

                <div>
                  <h3 className="text-[14px] font-medium mb-0.5" style={{ color: t.ink, ...sans }}>03  提升建议</h3>
                  <p className="text-[13px] leading-relaxed" style={{ color: t.inkSecondary }}>给出个性化的学习和成长建议</p>
                </div>
              </div>
            </Card>

              {/* 小贴士 */}
              <div
                className="rounded-2xl p-5"
                style={{
                  background: t.accentSoft,
                  border: `1px solid ${t.accentSoft}`,
                }}
              >
                <h3 className="text-[14px] font-medium mb-2" style={{ color: t.button, ...sans }}>小贴士</h3>
                <p className="text-[13px] leading-relaxed" style={{ color: t.button }}>
                  粘贴完整的职位描述（包括职责和要求），能获得更精准的分析结果
                </p>
              </div>
            </div>
          </motion.div>
        </div>

        {/* 历史诊断 */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25, duration: 0.6, ease }}
          className="mb-16"
        >
          <Card>
            <div className="mb-6">
              <h2 className="text-[18px] font-medium" style={{ color: t.ink, ...sans }}>历史诊断</h2>
            </div>

            {history && history.length > 0 ? (
              <div className="space-y-0">
                {history.slice(0, 5).map((item, idx) => {
                  const q = matchQualitative(item.match_score)
                  return (
                    <div key={item.id}>
                      <button
                        onClick={() => navigate(`/jd-diagnosis/${item.id}`)}
                        className="w-full flex items-center justify-between py-4 text-left cursor-pointer group"
                        style={{
                          borderBottom: idx < Math.min(history.length, 5) - 1 ? `1px solid ${t.line}` : 'none',
                        }}
                      >
                        <div className="flex items-center gap-4">
                          <span
                            className="text-[13px] px-3 py-1 rounded-full font-medium"
                            style={{ background: t.accentSoft, color: t.button }}
                          >
                            {q.label}
                          </span>
                          <span
                            className="text-[14px] group-hover:underline"
                            style={{ color: t.ink, ...sans }}
                          >
                            {item.jd_title}
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-[12px]" style={{ color: t.inkMuted }}>
                            {formatDateShort(item.created_at)}
                          </span>
                          <ArrowRight
                            className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity"
                            style={{ color: t.inkMuted }}
                          />
                        </div>
                      </button>
                    </div>
                  )
                })}
              </div>
            ) : (
                <div className="py-12 text-center">
                  <div className="w-8 h-px mx-auto mb-4" style={{ background: t.line }} />
                <p className="text-[14px] mb-1" style={{ color: t.inkSecondary }}>还没有诊断记录</p>
                <p className="text-[13px]" style={{ color: t.inkMuted }}>从上方粘贴第一份 JD 开始</p>
              </div>
            )}
          </Card>
        </motion.div>
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
      <div className="max-w-[1440px] mx-auto px-6 md:px-12">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, ease }}
          className="pt-16 pb-12"
        >
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-1 text-[13px] hover:opacity-70 transition-opacity mb-8 cursor-pointer"
            style={{ color: t.inkMuted }}
          >
            <ChevronLeft className="w-4 h-4" />
            返回
          </button>

          <h1
            className="font-normal leading-[1.15] tracking-tight"
            style={{
              ...serif,
              color: t.ink,
              fontSize: 'clamp(28px, 4vw, 40px)',
              maxWidth: '700px',
            }}
          >
            {data.jd_title}
          </h1>

          <p className="mt-4 text-[13px]" style={{ color: t.inkMuted }}>
            诊断于 {formatDateShort(data.created_at)}
          </p>
        </motion.div>

        <Divider className="mb-12" />

        {/* 两栏布局 */}
        <div className="flex flex-col lg:flex-row gap-8 mb-16">
          {/* 左侧主内容 */}
          <div className="flex-[65] space-y-8">
            {/* 总分卡片 */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1, duration: 0.6, ease }}
            >
              <Card>
                <div className="flex items-start gap-8">
                  <div className="text-center">
                    <span
                      className="block font-normal leading-none"
                      style={{
                        ...serif,
                        color: t.accent,
                        fontSize: 'clamp(48px, 8vw, 72px)',
                      }}
                    >
                      {score}
                    </span>
                    <span className="block text-[12px] mt-2" style={{ color: t.inkMuted }}>匹配分</span>
                  </div>
                  <div className="pt-3">
                    <span
                      className="text-[14px] font-medium px-3 py-1 rounded-full"
                      style={{ background: t.accentSoft, color: t.button }}
                    >
                      {qual.label}
                    </span>
                    <p className="text-[13px] mt-3 leading-relaxed" style={{ color: t.inkSecondary }}>
                      {qual.desc}。已具备 <span style={{ color: t.button }}>{matchedCount}</span> 项核心技能
                      {gapsCount > 0 && <>，缺口 <span style={{ color: t.accent }}>{gapsCount}</span> 项</>}
                    </p>
                  </div>
                </div>
              </Card>
            </motion.div>

            {/* AI 影响分析 */}
            {graphContext && zoneCfg && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15, duration: 0.6, ease }}
              >
                <Card>
                  <h2 className="text-[18px] font-medium mb-5" style={{ color: t.ink, ...sans }}>AI 影响分析</h2>
                  <div className="flex items-center gap-3 mb-4">
                    <span
                      className="text-[13px] font-medium px-3 py-1 rounded-full"
                      style={{ background: t.accentSoft, color: zoneCfg.color }}
                    >
                      {zoneCfg.label}
                    </span>
                    <span className="text-[12px]" style={{ color: t.inkMuted }}>图谱定位：{graphContext.label}</span>
                  </div>
                  <p className="text-[13px] leading-[1.8] mb-5" style={{ color: t.inkSecondary }}>
                    {zoneCfg.desc}
                  </p>
                  <div className="flex items-center gap-6 text-[13px]" style={{ color: t.inkSecondary }}>
                    <span>替代压力 <span style={{ color: t.ink }}>{graphContext.replacement_pressure}</span>/100</span>
                    <span style={{ color: t.line }}>·</span>
                    <span>人+AI 协同 <span style={{ color: t.ink }}>{graphContext.human_ai_leverage}</span>/100</span>
                  </div>
                </Card>
              </motion.div>
            )}

            {/* 四维评估 */}
            {Object.keys(dimensions).length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2, duration: 0.6, ease }}
              >
                <Card>
                  <h2 className="text-[18px] font-medium mb-6" style={{ color: t.ink, ...sans }}>四维评估</h2>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
                    {Object.entries(dimensions).map(([key, dim]) => {
                      const lvl = dimLevel(dim.score ?? 0)
                      return (
                        <div key={key} className="text-center p-4 rounded-xl" style={{ background: t.bg }}>
                          <span
                            className="block font-normal leading-none mb-2"
                            style={{ ...serif, color: t.ink, fontSize: '32px' }}
                          >
                            {dim.score ?? 0}
                          </span>
                          <span className="block text-[12px] mb-1" style={{ color: t.inkMuted }}>
                            {dimLabelMap[key] || key}
                          </span>
                          <span className="text-[11px] font-medium" style={{ color: lvl.color }}>
                            {lvl.label}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                </Card>
              </motion.div>
            )}

            {/* 技能 */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              {matched.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.25, duration: 0.6, ease }}
                >
                  <Card className="h-full">
                    <h2 className="text-[18px] font-medium mb-5" style={{ color: t.ink, ...sans }}>
                      已匹配技能 <span className="text-[14px]" style={{ color: t.inkMuted }}>({matchedCount})</span>
                    </h2>
                    <div className="flex flex-wrap gap-2">
                      {matched.map((m) => (
                        <span
                          key={skillName(m)}
                          className="text-[13px] px-3 py-1.5 rounded-full"
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
                  transition={{ delay: 0.3, duration: 0.6, ease }}
                >
                  <Card className="h-full">
                    <h2 className="text-[18px] font-medium mb-5" style={{ color: t.ink, ...sans }}>
                      技能缺口 <span className="text-[14px]" style={{ color: t.inkMuted }}>({gapsCount})</span>
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
                            className="text-[13px] px-3 py-1.5 rounded-full flex items-center gap-1.5"
                            style={{
                              background: isHigh ? '#FEF2F0' : t.bg,
                              color: isHigh ? t.accent : t.inkSecondary,
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

            {/* 转岗路线 */}
            {graphContext?.escape_routes && graphContext.escape_routes.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35, duration: 0.6, ease }}
              >
                <Card>
                  <h2 className="text-[18px] font-medium mb-6" style={{ color: t.ink, ...sans }}>推荐转岗路线</h2>
                  <div className="space-y-0">
                    {graphContext.escape_routes.map((route, idx) => {
                      const routeZone = isZoneKey(route.target_zone) ? zoneMap[route.target_zone] : null
                      return (
                        <div
                          key={idx}
                          className="py-4"
                          style={{ borderBottom: idx < graphContext.escape_routes!.length - 1 ? `1px solid ${t.line}` : 'none' }}
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div>
                              <div className="flex items-center gap-3 mb-2">
                                <span className="text-[14px] font-medium" style={{ color: t.ink, ...sans }}>
                                  {route.target_label}
                                </span>
                                {routeZone && (
                                  <span
                                    className="text-[11px] font-medium px-2 py-0.5 rounded-full"
                                    style={{ background: t.accentSoft, color: routeZone.color }}
                                  >
                                    {routeZone.label}
                                  </span>
                                )}
                              </div>
                              <div className="flex flex-wrap gap-2">
                                {route.gap_skills.slice(0, 3).map((skill, sIdx) => (
                                  <span
                                    key={sIdx}
                                    className="text-[12px] px-2.5 py-1 rounded-full"
                                    style={{ background: t.bg, color: t.inkSecondary }}
                                  >
                                    {skill}
                                  </span>
                                ))}
                              </div>
                            </div>
                            <span className="text-[12px] shrink-0" style={{ color: t.inkMuted }}>
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

            {/* 简历建议 */}
            {tips.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4, duration: 0.6, ease }}
              >
                <Card>
                  <h2 className="text-[18px] font-medium mb-6" style={{ color: t.ink, ...sans }}>简历优化建议</h2>
                  <div className="space-y-4">
                    {tips.map((tip, i) => (
                      <div key={i} className="flex gap-4">
                        <span
                          className="text-[12px] font-medium shrink-0 w-6 h-6 rounded-full flex items-center justify-center"
                          style={{ background: t.accentSoft, color: t.button }}
                        >
                          {i + 1}
                        </span>
                        <p className="text-[13px] leading-[1.8]" style={{ color: t.inkSecondary }}>
                          {tip}
                        </p>
                      </div>
                    ))}
                  </div>
                </Card>
              </motion.div>
            )}

            {data.coach_insight && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.42, duration: 0.6, ease }}
              >
                <CoachInsightCard insight={data.coach_insight} delay={0} />
              </motion.div>
            )}

            {/* 面试入口 */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.45, duration: 0.6, ease }}
            >
              <Card>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[14px] font-medium mb-1" style={{ color: t.ink, ...sans }}>
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
                    className="px-5 py-2.5 rounded-lg text-white text-[13px] font-medium cursor-pointer transition-all"
                    style={{ background: t.button }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = t.buttonHover
                      e.currentTarget.style.transform = 'translateY(-1px)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = t.button
                      e.currentTarget.style.transform = 'translateY(0)'
                    }}
                  >
                    开始面试
                  </button>
                </div>
              </Card>
            </motion.div>
          </div>

          {/* 右侧边栏 */}
          <div className="flex-[35]">
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, duration: 0.6, ease }}
              className="sticky top-24 space-y-6"
            >
              <Card>
                <h2 className="text-[18px] font-medium mb-6" style={{ color: t.ink, ...sans }}>诊断概览</h2>
                <div className="space-y-5">
                  <div className="flex items-baseline justify-between">
                    <span className="text-[13px]" style={{ color: t.inkSecondary }}>匹配得分</span>
                    <span className="font-normal" style={{ ...serif, color: t.accent, fontSize: '28px' }}>{score}</span>
                  </div>
                  <Divider />
                  <div className="flex items-baseline justify-between">
                    <span className="text-[13px]" style={{ color: t.inkSecondary }}>已匹配技能</span>
                    <span className="text-[14px] font-medium" style={{ color: t.ink }}>{matchedCount} 项</span>
                  </div>
                  <Divider />
                  <div className="flex items-baseline justify-between">
                    <span className="text-[13px]" style={{ color: t.inkSecondary }}>技能缺口</span>
                    <span className="text-[14px] font-medium" style={{ color: t.accent }}>{gapsCount} 项</span>
                  </div>
                  <Divider />
                  <div className="flex items-baseline justify-between">
                    <span className="text-[13px]" style={{ color: t.inkSecondary }}>评估维度</span>
                    <span className="text-[14px] font-medium" style={{ color: t.ink }}>{Object.keys(dimensions).length} 项</span>
                  </div>
                </div>
              </Card>

              <div
                className="rounded-2xl p-5"
                style={{
                  background: t.accentSoft,
                  border: `1px solid ${t.accentSoft}`,
                }}
              >
                <h3 className="text-[14px] font-medium mb-2" style={{ color: t.button, ...sans }}>小贴士</h3>
                <p className="text-[13px] leading-relaxed" style={{ color: t.button }}>
                  针对技能缺口进行重点准备，可以显著提升面试通过率。建议优先补足标记为"高优先级"的技能项。
                </p>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  )
}