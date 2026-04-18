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
} from 'lucide-react'
import { getJDDiagnosis, listJDDiagnoses, type JDDiagnosisDetail } from '@/api/jd'
import { useAuth } from '@/hooks/useAuth'
import { useProfileData } from '@/hooks/useProfileData'

const ease = [0.23, 1, 0.32, 1] as const

function scoreColor(s: number) {
  return s >= 80 ? 'text-emerald-600' : s >= 60 ? 'text-blue-600' : s >= 40 ? 'text-amber-600' : 'text-red-500'
}

function barColor(s: number) {
  return s >= 80 ? 'bg-emerald-400' : s >= 60 ? 'bg-blue-400' : s >= 40 ? 'bg-amber-400' : 'bg-red-400'
}

const zoneMap: Record<string, { label: string; color: string; bg: string; desc: string }> = {
  leverage:   { label: '协同优势区', color: 'text-emerald-700', bg: 'bg-emerald-50', desc: 'AI 增强人，人+AI 协同效应最强' },
  transition: { label: '转型过渡区', color: 'text-blue-700',    bg: 'bg-blue-50',    desc: '部分任务自动化，需要主动转型' },
  caution:    { label: '替代警惕区', color: 'text-amber-700',   bg: 'bg-amber-50',   desc: 'AI 替代压力较高，建议提前准备' },
  critical:   { label: '关键防御区', color: 'text-red-700',     bg: 'bg-red-50',     desc: 'AI 难以替代，但需持续深耕' },
}

export default function JDDiagnosisPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [jdInput, setJdInput] = useState('')

  const diagnosisId = id ? parseInt(id, 10) : null

  const { data, isLoading, error } = useQuery({
    queryKey: ['jd-diagnosis', diagnosisId],
    queryFn: () => getJDDiagnosis(diagnosisId!),
    enabled: !!diagnosisId && !isNaN(diagnosisId),
    staleTime: 60_000,
  })

  if (!diagnosisId || isNaN(diagnosisId)) {
    return <JDInputForm jdInput={jdInput} setJdInput={setJdInput} />
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

  return (
    <div className="h-full w-full overflow-y-auto">
      <div className="max-w-[720px] mx-auto px-6 py-8">
        {/* Header */}
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
            诊断于 {data.created_at.slice(0, 10)}
          </p>
        </motion.div>

        {/* Match Score */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05, duration: 0.4, ease }}
          className="glass p-6 mb-6"
        >
          <div className="flex items-center gap-6">
            <div className="text-center shrink-0">
              <p className={`text-[48px] font-black leading-none tabular-nums ${scoreColor(score)}`}>
                {score}<span className="text-[20px] font-bold">%</span>
              </p>
              <p className="text-[12px] text-slate-400 mt-1.5 font-medium">匹配度</p>
            </div>
            <div className="flex-1 min-w-0">
              <div className="h-3 bg-slate-100 rounded-full overflow-hidden mb-3">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${score}%` }}
                  transition={{ duration: 0.8, ease }}
                  className={`h-full rounded-full ${barColor(score)}`}
                />
              </div>
              <p className="text-[13px] text-slate-600">
                已具备 <span className="font-semibold text-emerald-600">{matchedCount}</span> 项核心技能
                {gapsCount > 0 && (
                  <>，缺口 <span className="font-semibold text-amber-600">{gapsCount}</span> 项</>
                )}
              </p>
            </div>
          </div>
        </motion.div>

        {/* AI Impact Analysis */}
        {graphContext && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.4, ease }}
            className="glass p-6 mb-6"
          >
            <h3 className="text-[13px] font-bold text-slate-700 mb-3">AI 影响分析</h3>
            <p className="text-[13px] text-slate-600 mb-2">
              图谱定位：{graphContext.label} · 节点 #{graphContext.node_id}
            </p>
            <span
              className={`inline-block px-2 py-0.5 rounded-md text-[12px] font-medium ${zoneMap[graphContext.zone]?.bg || 'bg-slate-50'} ${zoneMap[graphContext.zone]?.color || 'text-slate-600'}`}
            >
              {zoneMap[graphContext.zone]?.label || graphContext.zone}
            </span>

            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[12px] text-slate-600">AI 替代压力</span>
                  <span className="text-[12px] font-bold text-slate-700">{graphContext.replacement_pressure}/100</span>
                </div>
                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${graphContext.replacement_pressure}%` }}
                    transition={{ duration: 0.8, ease }}
                    className={`h-full rounded-full ${barColor(graphContext.replacement_pressure)}`}
                  />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[12px] text-slate-600">人+AI 协同</span>
                  <span className="text-[12px] font-bold text-slate-700">{graphContext.human_ai_leverage}/100</span>
                </div>
                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${graphContext.human_ai_leverage}%` }}
                    transition={{ duration: 0.8, ease }}
                    className={`h-full rounded-full ${barColor(graphContext.human_ai_leverage)}`}
                  />
                </div>
              </div>
            </div>

            <p className="mt-3 text-[13px] text-slate-500">
              {zoneMap[graphContext.zone]?.desc || ''}
            </p>
          </motion.div>
        )}

        {/* Dimensions */}
        {Object.keys(dimensions).length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.4, ease }}
            className="glass p-6 mb-6"
          >
            <h3 className="text-[13px] font-bold text-slate-700 mb-4">四维评分</h3>
            <div className="space-y-3">
              {Object.entries(dimensions).map(([key, dim]) => {
                const labelMap: Record<string, string> = {
                  foundation: '基础素养', skill: '技能匹配', potential: '成长潜力', soft_skill: '软技能'
                }
                const s = dim.score ?? 0
                return (
                  <div key={key} className="flex items-center gap-3">
                    <span className="text-[12px] text-slate-600 w-16 shrink-0 font-medium">
                      {labelMap[key] || key}
                    </span>
                    <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${barColor(s)}`}
                        style={{ width: `${s}%` }}
                      />
                    </div>
                    <span className="text-[12px] font-bold text-slate-600 w-8 text-right">{s}</span>
                  </div>
                )
              })}
            </div>
          </motion.div>
        )}

        {/* Skills */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
          {/* Matched */}
          {matched.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25, duration: 0.4, ease }}
              className="glass p-5"
            >
              <h3 className="text-[13px] font-bold text-emerald-700 mb-3 flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5" />
                已匹配技能
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {matched.map((m, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 text-[12px] font-medium"
                  >
                    {typeof m === 'string' ? m : m.skill}
                  </span>
                ))}
              </div>
            </motion.div>
          )}

          {/* Gaps */}
          {gaps.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.4, ease }}
              className="glass p-5"
            >
              <h3 className="text-[13px] font-bold text-amber-700 mb-3 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5" />
                技能缺口
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {gaps.map((g, idx) => (
                  <span
                    key={idx}
                    className={`px-2 py-0.5 rounded-md text-[12px] font-medium ${
                      (typeof g === 'object' && g !== null && 'priority' in g && g.priority === 'high')
                        ? 'bg-red-50 text-red-700'
                        : 'bg-amber-50 text-amber-700'
                    }`}
                  >
                    {typeof g === 'string' ? g : g.skill}
                  </span>
                ))}
              </div>
            </motion.div>
          )}
        </div>

        {/* Escape Routes */}
        {graphContext?.escape_routes && graphContext.escape_routes.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35, duration: 0.4, ease }}
            className="glass p-6 mb-6"
          >
            <h3 className="text-[13px] font-bold text-slate-700 mb-4">推荐转岗路线</h3>
            <div className="divide-y divide-slate-100">
              {graphContext.escape_routes.map((route, idx) => (
                <div key={idx} className="py-3 first:pt-0 last:pb-0">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1.5">
                        <span className="text-[13px] font-semibold text-slate-700">{route.target_label}</span>
                        <span
                          className={`px-1.5 py-0.5 rounded text-[11px] font-medium ${zoneMap[route.target_zone]?.bg || 'bg-slate-50'} ${zoneMap[route.target_zone]?.color || 'text-slate-600'}`}
                        >
                          {zoneMap[route.target_zone]?.label || route.target_zone}
                        </span>
                        {route.tag && <span className="text-[12px] text-slate-400">{route.tag}</span>}
                      </div>
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="text-[12px] text-slate-500">需补：</span>
                        {route.gap_skills.slice(0, 3).map((skill, sIdx) => (
                          <span key={sIdx} className="px-1.5 py-0.5 rounded bg-slate-50 text-slate-600 text-[11px]">
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
              ))}
            </div>
          </motion.div>
        )}

        {/* Resume Tips */}
        {tips.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35, duration: 0.4, ease }}
            className="glass p-6 mb-6"
          >
            <h3 className="text-[13px] font-bold text-slate-700 mb-3">简历优化建议</h3>
            <ul className="space-y-2">
              {tips.map((tip, i) => (
                <li key={i} className="flex items-start gap-2 text-[13px] text-slate-600">
                  <span className="text-blue-400 mt-0.5 shrink-0">{i + 1}.</span>
                  {tip}
                </li>
              ))}
            </ul>
          </motion.div>
        )}

        {/* CTA */}
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
              <p className="text-[14px] font-semibold text-slate-700">针对这份 JD 模拟面试</p>
              <p className="text-[12px] text-slate-400">重点考察 {gapsCount} 项技能缺口</p>
            </div>
          </div>
          <button
            onClick={() => navigate(`/interview?role=${encodeURIComponent(data.jd_title)}&jd=${encodeURIComponent(data.jd_text.slice(0, 500))}`)}
            className="px-5 py-2.5 rounded-xl bg-[var(--blue)] text-white text-[13px] font-semibold hover:brightness-110 transition-all cursor-pointer shrink-0"
          >
            开始面试
          </button>
        </motion.div>
      </div>
    </div>
  )
}

// ── JD Input Form (when no id provided) ──
function JDInputForm({ jdInput, setJdInput }: { jdInput: string; setJdInput: (v: string) => void }) {
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)
  const { token } = useAuth()
  const { profile } = useProfileData(token)

  const { data: history } = useQuery({
    queryKey: ['jd-diagnosis-history'],
    queryFn: () => listJDDiagnoses(),
  })

  const handleSubmit = async () => {
    if (!jdInput.trim()) return
    setSubmitting(true)
    try {
      const { diagnoseJd } = await import('@/api/jd')
      const result = await diagnoseJd({ jd_text: jdInput })
      navigate(`/jd-diagnosis/${result.id}`, { replace: true })
    } catch (e) {
      alert(e instanceof Error ? e.message : '诊断失败')
      setSubmitting(false)
    }
  }

  const targetLabel = profile?.career_goals?.[0]?.target_label ?? profile?.graph_position?.target_label
  const skillCount = profile?.profile?.skills?.length ?? 0
  const historyCount = history?.length ?? 0

  return (
    <div className="h-full w-full overflow-y-auto">
      <div className="max-w-[640px] mx-auto px-6 py-8">
        {/* ── Header ── */}
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

        {/* ── Profile Snapshot ── */}
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
              <p className="text-[14px] font-bold text-slate-800">当前画像</p>
              <p className="text-[12px] text-slate-400">基于你的简历和目标方向</p>
            </div>
          </div>
          <div className="flex items-center gap-5 px-2">
            <div className="flex items-center gap-2">
              <Briefcase className="w-3.5 h-3.5 text-slate-300" />
              <span className="text-[13px] text-slate-500">目标：</span>
              {targetLabel ? (
                <span className="text-[13px] font-semibold text-slate-700">{targetLabel}</span>
              ) : (
                <button
                  onClick={() => navigate('/graph')}
                  className="text-[13px] font-semibold text-[var(--blue)] hover:underline cursor-pointer"
                >
                  去选定
                </button>
              )}
            </div>
            <div className="w-px h-4 bg-slate-200" />
            <div className="flex items-center gap-2">
              <TrendingUp className="w-3.5 h-3.5 text-slate-300" />
              <span className="text-[13px] text-slate-500">技能：</span>
              <span className="text-[13px] font-semibold text-slate-700">{skillCount} 项</span>
            </div>
            <div className="w-px h-4 bg-slate-200" />
            <div className="flex items-center gap-2">
              <FileText className="w-3.5 h-3.5 text-slate-300" />
              <span className="text-[13px] text-slate-500">历史：</span>
              <span className="text-[13px] font-semibold text-slate-700">{historyCount} 次</span>
            </div>
          </div>
        </motion.div>

        {/* ── Paste JD ── */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.4, ease }}
          className="glass p-5 mb-4"
        >
          <div className="flex items-center gap-2 mb-3">
            <Target className="w-4 h-4 text-slate-400" />
            <p className="text-[14px] font-bold text-slate-800">粘贴招聘要求</p>
          </div>
          <textarea
            value={jdInput}
            onChange={(e) => setJdInput(e.target.value)}
            placeholder="把目标岗位的招聘要求全文粘贴到这里..."
            rows={6}
            className="w-full px-4 py-3 rounded-lg border border-slate-200/60 bg-white/50 text-[14px] text-slate-800 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300/60 transition-all resize-none leading-relaxed"
          />
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

        {/* ── History ── */}
        {history && history.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.4, ease }}
            className="glass p-5"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-slate-400" />
                <p className="text-[14px] font-bold text-slate-800">历史诊断</p>
              </div>
              <span className="text-[12px] text-slate-400">共 {history.length} 次</span>
            </div>
            <div className="space-y-2">
              {history.slice(0, 5).map((item) => (
                <button
                  key={item.id}
                  onClick={() => navigate(`/jd-diagnosis/${item.id}`)}
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/40 transition-colors cursor-pointer text-left group"
                >
                  <span className={`text-[16px] font-black tabular-nums w-12 text-right shrink-0 ${scoreColor(item.match_score)}`}>
                    {item.match_score}
                  </span>
                  <span className="text-[12px] text-slate-400 font-medium">分</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] font-semibold text-slate-700 truncate group-hover:text-[var(--blue)] transition-colors">
                      {item.jd_title}
                    </p>
                  </div>
                  <span className="text-[12px] text-slate-400 shrink-0">
                    {item.created_at.slice(0, 10)}
                  </span>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-300 group-hover:text-[var(--blue)] group-hover:translate-x-0.5 transition-all shrink-0" />
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  )
}
