import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  ChevronLeft,
  MessageSquare,
  Target,
  CheckCircle,
  AlertTriangle,
  User,
  Briefcase,
  FileText,
  ArrowRight,
  Clock,
  TrendingUp,
  Sparkles,
  ClipboardPaste,
  MousePointerClick,
  Wand2,
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

const ease = [0.23, 1, 0.32, 1] as const

/* ── Score helpers ── */
function scoreColor(s: number) {
  return s >= 80
    ? 'text-emerald-600'
    : s >= 60
      ? 'text-blue-600'
      : s >= 40
        ? 'text-amber-600'
        : 'text-red-500'
}

function matchQualitative(score: number) {
  if (score >= 80)
    return {
      label: '高度匹配',
      color: 'text-emerald-700',
      bg: 'bg-emerald-50',
      border: 'border-emerald-200',
      desc: '核心技能基本覆盖，竞争力较强',
    }
  if (score >= 60)
    return {
      label: '基础匹配',
      color: 'text-blue-700',
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      desc: '具备基础能力，有若干可补强项',
    }
  if (score >= 40)
    return {
      label: '需补强',
      color: 'text-amber-700',
      bg: 'bg-amber-50',
      border: 'border-amber-200',
      desc: '有一定基础，但核心缺口较多',
    }
  return {
    label: '差距较大',
    color: 'text-red-700',
    bg: 'bg-red-50',
    border: 'border-red-200',
    desc: '技能覆盖度低，建议先补基础',
  }
}

function dimLevel(s: number) {
  if (s >= 80) return { label: '强', color: 'text-emerald-700', bg: 'bg-emerald-50' }
  if (s >= 60) return { label: '中', color: 'text-blue-700', bg: 'bg-blue-50' }
  if (s >= 40) return { label: '弱', color: 'text-amber-700', bg: 'bg-amber-50' }
  return { label: '缺', color: 'text-red-700', bg: 'bg-red-50' }
}

/* ── Zone config ── */
const ZONE_KEYS = ['leverage', 'transition', 'caution', 'critical'] as const
type ZoneKey = (typeof ZONE_KEYS)[number]

const zoneMap: Record<
  ZoneKey,
  { label: string; color: string; bg: string; desc: string }
> = {
  leverage: {
    label: '协同优势区',
    color: 'text-emerald-700',
    bg: 'bg-emerald-50',
    desc: 'AI 增强人，人+AI 协同效应最强',
  },
  transition: {
    label: '转型过渡区',
    color: 'text-blue-700',
    bg: 'bg-blue-50',
    desc: '部分任务自动化，需要主动转型',
  },
  caution: {
    label: '替代警惕区',
    color: 'text-amber-700',
    bg: 'bg-amber-50',
    desc: 'AI 替代压力较高，建议提前准备',
  },
  critical: {
    label: '关键防御区',
    color: 'text-red-700',
    bg: 'bg-red-50',
    desc: 'AI 难以替代，但需持续深耕',
  },
}

function isZoneKey(z: string): z is ZoneKey {
  return ZONE_KEYS.includes(z as ZoneKey)
}

/* ── Dimension label map ── */
const dimLabelMap: Record<string, string> = {
  foundation: '基础素养',
  skill: '技能匹配',
  potential: '成长潜力',
  soft_skill: '软技能',
}

/* ── Sample JDs ── */
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

/* ── Skill name extractor ── */
function skillName(item: string | { skill: string }): string {
  return typeof item === 'string' ? item : item.skill
}

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
    return <JDInputForm />
  }

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="glass p-8 flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-[14px] text-slate-500">加载诊断结果...</span>
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="glass p-8 text-center">
          <p className="text-[14px] text-red-600 mb-3">加载失败</p>
          <button
            onClick={() => navigate(-1)}
            className="px-4 py-2 rounded-lg bg-blue-600 text-white text-[13px] font-medium cursor-pointer"
          >
            返回
          </button>
        </div>
      </div>
    )
  }

  return <DiagnosisResult data={data} />
}

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
      <div className="max-w-[720px] mx-auto px-6 py-8">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease }}
          className="mb-6"
        >
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-1 text-[13px] text-slate-400 hover:text-slate-700 transition-colors cursor-pointer mb-4"
          >
            <ChevronLeft className="w-4 h-4" />
            返回
          </button>
          <h1 className="text-[24px] font-bold text-slate-900 tracking-tight">
            {data.jd_title}
          </h1>
          <p className="text-[13px] text-slate-400 mt-1">
            诊断于 {formatDateShort(data.created_at)}
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05, duration: 0.4, ease }}
          className="glass p-6 mb-5"
        >
          <div className="flex items-start gap-4">
            <div
              className={`shrink-0 px-3 py-1.5 rounded-lg ${qual.bg} border ${qual.border}`}
            >
              <span className={`text-[13px] font-bold ${qual.color}`}>
                {qual.label}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[13px] text-slate-600 leading-relaxed">
                {qual.desc}。已具备{' '}
                <span className="font-semibold text-emerald-600">
                  {matchedCount}
                </span>{' '}
                项核心技能
                {gapsCount > 0 && (
                  <>
                    ，缺口{' '}
                    <span className="font-semibold text-amber-600">
                      {gapsCount}
                    </span>{' '}
                    项
                  </>
                )}
                。
              </p>
            </div>
          </div>
        </motion.div>

        {graphContext && zoneCfg && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.4, ease }}
            className="glass p-6 mb-5"
          >
            <h3 className="text-[13px] font-bold text-slate-700 mb-3">
              AI 影响分析
            </h3>
            <div className="flex items-center gap-2 mb-2">
              <span
                className={`inline-block px-2 py-0.5 rounded-md text-[12px] font-medium ${zoneCfg.bg} ${zoneCfg.color}`}
              >
                {zoneCfg.label}
              </span>
              <span className="text-[12px] text-slate-400">
                图谱定位：{graphContext.label}
              </span>
            </div>
            <p className="text-[13px] text-slate-500">{zoneCfg.desc}</p>
            <div className="mt-3 flex items-center gap-4 text-[12px] text-slate-500">
              <span>
                替代压力{' '}
                <span className="font-semibold text-slate-700">
                  {graphContext.replacement_pressure}
                </span>
                /100
              </span>
              <span className="text-slate-200">|</span>
              <span>
                人+AI 协同{' '}
                <span className="font-semibold text-slate-700">
                  {graphContext.human_ai_leverage}
                </span>
                /100
              </span>
            </div>
          </motion.div>
        )}

        {Object.keys(dimensions).length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.4, ease }}
            className="glass p-6 mb-5"
          >
            <h3 className="text-[13px] font-bold text-slate-700 mb-3">
              四维评估
            </h3>
            <div className="flex flex-wrap gap-2">
              {Object.entries(dimensions).map(([key, dim]) => {
                const lvl = dimLevel(dim.score ?? 0)
                return (
                  <div
                    key={key}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-100"
                  >
                    <span className="text-[12px] text-slate-500">
                      {dimLabelMap[key] || key}
                    </span>
                    <span className={`text-[12px] font-bold ${lvl.color}`}>
                      {lvl.label}
                    </span>
                  </div>
                )
              })}
            </div>
          </motion.div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
          {matched.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25, duration: 0.4, ease }}
              className="glass p-5"
            >
              <h3 className="text-[13px] font-bold text-emerald-700 mb-3 flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5" />
                已匹配技能 ({matched.length})
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {matched.map((m) => (
                  <span
                    key={skillName(m)}
                    className="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 text-[12px] font-medium border border-emerald-100"
                  >
                    {skillName(m)}
                  </span>
                ))}
              </div>
            </motion.div>
          )}

          {gaps.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.4, ease }}
              className="glass p-5"
            >
              <h3 className="text-[13px] font-bold text-amber-700 mb-3 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5" />
                技能缺口 ({gaps.length})
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {gaps.map((g) => {
                  const isHigh =
                    typeof g === 'object' &&
                    g !== null &&
                    'priority' in g &&
                    g.priority === 'high'
                  return (
                    <span
                      key={skillName(g)}
                      className={`px-2 py-0.5 rounded-md text-[12px] font-medium border ${
                        isHigh
                          ? 'bg-red-50 text-red-700 border-red-100'
                          : 'bg-amber-50 text-amber-700 border-amber-100'
                      }`}
                    >
                      {skillName(g)}
                    </span>
                  )
                })}
              </div>
            </motion.div>
          )}
        </div>

        {graphContext?.escape_routes && graphContext.escape_routes.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35, duration: 0.4, ease }}
            className="glass p-6 mb-5"
          >
            <h3 className="text-[13px] font-bold text-slate-700 mb-4">
              推荐转岗路线
            </h3>
            <div className="divide-y divide-slate-100">
              {graphContext.escape_routes.map((route, idx) => {
                const routeZone = isZoneKey(route.target_zone)
                  ? zoneMap[route.target_zone]
                  : null
                return (
                  <div key={idx} className="py-3 first:pt-0 last:pb-0">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap mb-1.5">
                          <span className="text-[13px] font-semibold text-slate-700">
                            {route.target_label}
                          </span>
                          {routeZone && (
                            <span
                              className={`px-1.5 py-0.5 rounded text-[11px] font-medium ${routeZone.bg} ${routeZone.color}`}
                            >
                              {routeZone.label}
                            </span>
                          )}
                          {route.tag && (
                            <span className="text-[12px] text-slate-400">
                              {route.tag}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-[12px] text-slate-500">
                            需补：
                          </span>
                          {route.gap_skills.slice(0, 3).map((skill, sIdx) => (
                            <span
                              key={sIdx}
                              className="px-1.5 py-0.5 rounded bg-slate-50 text-slate-600 text-[11px] border border-slate-100"
                            >
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                      <span className="text-[12px] text-slate-400 shrink-0 mt-0.5">
                        预估 {route.estimated_hours} 小时
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          </motion.div>
        )}

        {tips.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35, duration: 0.4, ease }}
            className="glass p-6 mb-5"
          >
            <h3 className="text-[13px] font-bold text-slate-700 mb-3">
              简历优化建议
            </h3>
            <ul className="space-y-2">
              {tips.map((tip, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-[13px] text-slate-600"
                >
                  <span className="text-blue-400 mt-0.5 shrink-0">
                    {i + 1}.
                  </span>
                  {tip}
                </li>
              ))}
            </ul>
          </motion.div>
        )}

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.4, ease }}
          className="glass p-5 flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <p className="text-[14px] font-semibold text-slate-700">
                针对这份 JD 模拟面试
              </p>
              <p className="text-[12px] text-slate-400">
                重点考察 {gapsCount} 项技能缺口
              </p>
            </div>
          </div>
          <button
            onClick={() =>
              navigate(
                `/interview?role=${encodeURIComponent(data.jd_title)}&jd=${encodeURIComponent(data.jd_text.slice(0, 200))}`,
              )
            }
            className="px-5 py-2.5 rounded-xl bg-[var(--blue)] text-white text-[13px] font-semibold hover:brightness-110 transition-all cursor-pointer shrink-0"
          >
            开始面试
          </button>
        </motion.div>
      </div>
    </div>
  )
}

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
      <div className="max-w-[640px] mx-auto px-6 py-8">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease }}
          className="mb-5"
        >
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-1 text-[13px] text-slate-400 hover:text-slate-700 transition-colors cursor-pointer mb-4"
          >
            <ChevronLeft className="w-4 h-4" />
            返回
          </button>
          <h1 className="text-[24px] font-bold text-slate-900 tracking-tight mb-1.5">
            JD 诊断
          </h1>
          <p className="text-[14px] text-slate-400">
            粘贴招聘要求，分析你与岗位的匹配度和技能缺口
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05, duration: 0.4, ease }}
          className="glass p-5 mb-4"
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-lg bg-[var(--blue)]/10 flex items-center justify-center">
              <User className="w-4 h-4 text-[var(--blue)]" />
            </div>
            <div>
              <p className="text-[14px] font-bold text-slate-800">
                当前画像
              </p>
              <p className="text-[12px] text-slate-400">
                基于你的简历和目标方向
              </p>
            </div>
          </div>

          {hasProfile ? (
            <div className="flex items-center gap-5 px-2">
              <div className="flex items-center gap-2">
                <Briefcase className="w-3.5 h-3.5 text-slate-300" />
                <span className="text-[13px] text-slate-500">目标：</span>
                <span className="text-[13px] font-semibold text-slate-700">
                  {targetLabel}
                </span>
              </div>
              <div className="w-px h-4 bg-slate-200" />
              <div className="flex items-center gap-2">
                <TrendingUp className="w-3.5 h-3.5 text-slate-300" />
                <span className="text-[13px] text-slate-500">技能：</span>
                <span className="text-[13px] font-semibold text-slate-700">
                  {skillCount} 项
                </span>
              </div>
              <div className="w-px h-4 bg-slate-200" />
              <div className="flex items-center gap-2">
                <FileText className="w-3.5 h-3.5 text-slate-300" />
                <span className="text-[13px] text-slate-500">历史：</span>
                <span className="text-[13px] font-semibold text-slate-700">
                  {historyCount} 次
                </span>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between px-2 py-2 rounded-lg bg-amber-50/60 border border-amber-100">
              <p className="text-[13px] text-amber-700">
                画像信息较空，诊断结果可能不够准确
              </p>
              <button
                onClick={() => navigate('/profile')}
                className="text-[13px] font-semibold text-[var(--blue)] hover:underline cursor-pointer shrink-0 ml-3"
              >
                去完善
              </button>
            </div>
          )}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.4, ease }}
          className="glass p-5 mb-4"
        >
          <div className="flex items-center gap-2 mb-3">
            <Target className="w-4 h-4 text-slate-400" />
            <p className="text-[14px] font-bold text-slate-800">
              粘贴招聘要求
            </p>
          </div>

          <div className="mb-3">
            <p className="text-[12px] text-slate-400 mb-2 flex items-center gap-1">
              <Sparkles className="w-3 h-3" />
              没现成的？选一个示例试试
            </p>
            <div className="flex flex-wrap gap-2">
              {sampleJDs.map((sample) => (
                <button
                  key={sample.label}
                  onClick={() => setJdInput(sample.text)}
                  className="px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-100 text-[12px] text-slate-600 hover:bg-blue-50 hover:border-blue-200 hover:text-blue-600 transition-all cursor-pointer"
                >
                  {sample.label}
                </button>
              ))}
            </div>
          </div>

          <textarea
            value={jdInput}
            onChange={(e) => setJdInput(e.target.value)}
            placeholder="把目标岗位的招聘要求全文粘贴到这里..."
            rows={6}
            className="w-full px-4 py-3 rounded-lg border border-slate-200/60 bg-white/50 text-[14px] text-slate-800 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300/60 transition-all resize-none leading-relaxed"
          />

          <div className="mt-3 flex items-center gap-1 text-[12px] text-slate-400">
            <ClipboardPaste className="w-3 h-3" />
            <span>复制 JD 全文</span>
            <span className="text-slate-200 mx-1">→</span>
            <MousePointerClick className="w-3 h-3" />
            <span>粘贴到上方</span>
            <span className="text-slate-200 mx-1">→</span>
            <Wand2 className="w-3 h-3" />
            <span>开始诊断</span>
          </div>

          {submitError && (
            <div className="mt-3 px-3 py-2 rounded-lg bg-red-50 border border-red-100 text-[13px] text-red-600">
              {submitError}
            </div>
          )}

          <div className="flex justify-end mt-3">
            <button
              onClick={handleSubmit}
              disabled={!jdInput.trim() || submitting}
              className="px-6 py-2.5 rounded-xl bg-[var(--blue)] text-white text-[14px] font-semibold hover:brightness-110 transition-all disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
            >
              {submitting ? '分析中...' : '开始诊断'}
            </button>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.4, ease }}
          className="glass p-5"
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-slate-400" />
              <p className="text-[14px] font-bold text-slate-800">
                历史诊断
              </p>
            </div>
            {history && history.length > 0 && (
              <span className="text-[12px] text-slate-400">
                共 {history.length} 次
              </span>
            )}
          </div>

          {history && history.length > 0 ? (
            <div className="space-y-2">
              {history.slice(0, 5).map((item) => {
                const q = matchQualitative(item.match_score)
                return (
                  <button
                    key={item.id}
                    onClick={() => navigate(`/jd-diagnosis/${item.id}`)}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/40 transition-colors cursor-pointer text-left group"
                  >
                    <span
                      className={`text-[13px] font-bold px-2 py-0.5 rounded-md ${q.bg} ${q.color} shrink-0`}
                    >
                      {q.label}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-[13px] font-semibold text-slate-700 truncate group-hover:text-[var(--blue)] transition-colors">
                        {item.jd_title}
                      </p>
                    </div>
                    <span className="text-[12px] text-slate-400 shrink-0">
                      {formatDateShort(item.created_at)}
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-300 group-hover:text-[var(--blue)] group-hover:translate-x-0.5 transition-all shrink-0" />
                  </button>
                )
              })}
            </div>
          ) : (
            <div className="py-6 text-center">
              <p className="text-[13px] text-slate-400 mb-1">
                还没有诊断记录
              </p>
              <p className="text-[12px] text-slate-300">
                从上方粘贴第一份 JD 开始
              </p>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}
