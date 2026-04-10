import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { rawFetch } from '@/api/client'
import { ArrowLeft, CheckCircle2, XCircle, AlertTriangle, Trash2, FileText, TrendingUp, Target, BookOpen, Search } from 'lucide-react'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { sendToCoach } from '@/hooks/useCoachTrigger'

/* ── Types ── */

interface GapSkill {
  skill: string
  priority: string
  match_delta: number
}

interface StructuredDetail {
  _structured?: boolean
  match_score?: number
  matched_skills?: string[]
  gap_skills?: GapSkill[]
  jd_title?: string
  raw_text?: string
}

interface CoachResultData {
  id: number
  result_type: string
  title: string
  summary: string
  detail: StructuredDetail
  metadata: Record<string, unknown>
  created_at: string
}

interface CoachResultItem {
  id: number
  result_type: string
  title: string
  summary: string
  metadata: Record<string, unknown>
  created_at: string
}

/* ── Constants ── */

const typeConfig: Record<string, { label: string; color: string; bg: string }> = {
  jd_diagnosis:       { label: 'JD 诊断',   color: 'text-blue-600',    bg: 'bg-blue-50' },
  career_report:      { label: '职业报告',   color: 'text-indigo-600',  bg: 'bg-indigo-50' },
  growth_analysis:    { label: '成长分析',   color: 'text-emerald-600', bg: 'bg-emerald-50' },
  interview_review:   { label: '面试复盘',   color: 'text-amber-600',   bg: 'bg-amber-50' },
  career_exploration: { label: '方向探索',   color: 'text-purple-600',  bg: 'bg-purple-50' },
  profile_analysis:   { label: '画像分析',   color: 'text-teal-600',    bg: 'bg-teal-50' },
  general:            { label: '分析结果',   color: 'text-slate-600',   bg: 'bg-slate-50' },
}

const priorityConfig: Record<string, { label: string; color: string; dot: string }> = {
  high:   { label: '高优先', color: 'text-red-600',   dot: 'bg-red-400' },
  medium: { label: '中优先', color: 'text-amber-600', dot: 'bg-amber-400' },
  low:    { label: '低优先', color: 'text-slate-500', dot: 'bg-slate-300' },
}

const ease = [0.23, 1, 0.32, 1] as const

function scoreColor(s: number) { return s >= 80 ? 'text-emerald-600' : s >= 60 ? 'text-blue-600' : s >= 40 ? 'text-amber-600' : 'text-red-500' }
function barColor(s: number) { return s >= 80 ? 'bg-emerald-400' : s >= 60 ? 'bg-blue-400' : s >= 40 ? 'bg-amber-400' : 'bg-red-400' }


/* ═══════════════════════════════════════════════
   Structured JD Diagnosis View
   ═══════════════════════════════════════════════ */

interface NextStep {
  icon: React.ReactNode
  label: string
  desc: string
  onClick: () => void
}

function JDDiagnosisView({ detail, nextSteps }: { detail: StructuredDetail; nextSteps: NextStep[] }) {
  const score = detail.match_score ?? 0
  const matched = detail.matched_skills ?? []
  const gaps = detail.gap_skills ?? []
  // Readiness: ratio of matched skills to total required
  const totalSkills = matched.length + gaps.length
  const readiness = totalSkills > 0 ? Math.round((matched.length / totalSkills) * 100) : score
  const highPriGaps = gaps.filter(g => g.priority === 'high')

  return (
    <>
      {/* Readiness hero */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05, duration: 0.4, ease }}
        className="glass p-6 mb-6"
      >
        <div className="flex items-center gap-6">
          <div className="text-center shrink-0">
            <p className={`text-[48px] font-black leading-none tabular-nums ${scoreColor(readiness)}`}>
              {readiness}<span className="text-[20px] font-bold">%</span>
            </p>
            <p className="text-[12px] text-slate-400 mt-1.5 font-medium">准备度</p>
          </div>
          <div className="flex-1 min-w-0">
            <div className="h-3 bg-slate-100 rounded-full overflow-hidden mb-3">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${readiness}%` }}
                transition={{ duration: 0.8, ease }}
                className={`h-full rounded-full ${barColor(readiness)}`}
              />
            </div>
            <p className="text-[13px] text-slate-600 mb-1">
              已具备 <span className="font-semibold text-emerald-600">{matched.length}</span> 项核心技能
              {gaps.length > 0 && (
                <>，再补 <span className="font-semibold text-amber-600">{gaps.length}</span> 项即可达标</>
              )}
            </p>
            {highPriGaps.length > 0 && (
              <p className="text-[12px] text-slate-400">
                优先补：{highPriGaps.slice(0, 3).map(g => g.skill).join('、')}
              </p>
            )}
          </div>
        </div>
      </motion.div>

      {/* Matched skills + Gap skills — in one glass card */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.12, duration: 0.4, ease }}
        className="glass p-6 mb-5"
      >
        <div className="g-inner space-y-5">
          {/* Matched */}
          {matched.length > 0 && (
            <div>
              <h2 className="text-[14px] font-bold text-slate-700 mb-2.5 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                你已具备的技能
              </h2>
              <div className="flex flex-wrap gap-2">
                {matched.map((skill) => (
                  <span key={skill} className="px-3 py-1 rounded-lg text-[13px] font-medium text-emerald-700 bg-emerald-500/10">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Divider */}
          {matched.length > 0 && gaps.length > 0 && <div className="h-px bg-slate-200/50" />}

          {/* Gaps */}
          {gaps.length > 0 && (
            <div>
              <h2 className="text-[14px] font-bold text-slate-700 mb-2.5 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                还需要补强的技能
              </h2>
              <div className="space-y-2">
                {gaps.map((gap, i) => {
                  const pri = priorityConfig[gap.priority] ?? priorityConfig.medium
                  return (
                    <motion.div
                      key={gap.skill}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.2 + i * 0.04, duration: 0.3, ease }}
                      className="flex items-center gap-3 px-4 py-3 rounded-xl bg-white/40 border border-white/50"
                    >
                      <span className={`w-2 h-2 rounded-full shrink-0 ${pri.dot}`} />
                      <span className="text-[14px] font-medium text-slate-800 flex-1">{gap.skill}</span>
                      <span className={`text-[11px] font-bold ${pri.color}`}>{pri.label}</span>
                      {gap.match_delta > 0 && (
                        <span className="flex items-center gap-0.5 text-[11px] font-medium text-blue-500">
                          <TrendingUp className="w-3 h-3" />+{gap.match_delta}%
                        </span>
                      )}
                    </motion.div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      </motion.div>

      {/* Overall assessment */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.4, ease }}
        className="glass p-5"
      >
        <div className="g-inner">
          <h2 className="text-[14px] font-bold text-slate-700 mb-2 flex items-center gap-2">
            <FileText className="w-4 h-4 text-slate-400" />
            综合评估
          </h2>
          <p className="text-[14px] text-slate-600 leading-[1.7]">
            {readiness >= 70
              ? `准备度 ${readiness}%，你已经具备这个岗位的大部分核心技能，可以开始投递了。简历中重点突出已掌握的 ${matched.length} 项技能，同时关注缺口技能的补强。`
              : readiness >= 40
              ? `准备度 ${readiness}%，基础不错，还需要补强 ${gaps.length} 项技能。建议先集中精力搞定${highPriGaps.length > 0 ? `「${highPriGaps[0].skill}」等 ${highPriGaps.length} 项高优先级缺口` : `最关键的 ${gaps[0] ? `「${gaps[0].skill}」` : '缺口技能'}`}，准备度过 70% 就可以开始投递了。`
              : `准备度 ${readiness}%，和这个岗位还有不小的差距。建议先补强 ${highPriGaps.length} 项高优先级技能，或者考虑寻找和你当前技能更匹配的方向。`
            }
          </p>
        </div>
      </motion.div>

      {/* Next steps */}
      {gaps.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.38, duration: 0.4, ease }}
          className="glass p-5 mt-5"
        >
          <div className="g-inner">
            <h2 className="text-[14px] font-bold text-slate-700 mb-3 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-blue-400" />
              下一步行动
            </h2>
            <div className="space-y-2">
              {nextSteps.map((step, i) => (
                <button
                  key={i}
                  onClick={step.onClick}
                  className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-white/40 border border-white/50 hover:border-blue-200 hover:bg-blue-50/30 transition-all cursor-pointer text-left group"
                >
                  <span className="shrink-0">{step.icon}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] font-semibold text-slate-700 group-hover:text-blue-600 transition-colors">{step.label}</p>
                    <p className="text-[11px] text-slate-400">{step.desc}</p>
                  </div>
                  <span className="text-[12px] text-slate-300 group-hover:text-blue-400 transition-colors shrink-0">→</span>
                </button>
              ))}
            </div>
          </div>
        </motion.div>
      )}
    </>
  )
}


/* ═══════════════════════════════════════════════
   Markdown view (for non-JD results)
   ═══════════════════════════════════════════════ */

function MarkdownView({ text, summary }: { text: string; summary: string }) {
  // Clean up common issues from AI output
  const cleaned = text
    .replace(/<br\s*\/?>/gi, '\n')  // <br> → newline
    .replace(/⭐/g, '')             // strip emoji stars
    .replace(/[💡✅⚠️❌🎯🔥📌]/g, '') // strip common emojis

  return (
    <>
      {summary && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05, duration: 0.4, ease }}
          className="glass p-5 mb-6"
        >
          <p className="text-[14px] text-slate-700 leading-relaxed">{summary}</p>
        </motion.div>
      )}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.12, duration: 0.4, ease }}
        className="glass p-6"
      >
        <div className="prose prose-slate prose-sm max-w-none
          prose-headings:text-slate-800 prose-headings:font-bold prose-headings:mb-3 prose-headings:mt-6 first:prose-headings:mt-0
          prose-h2:text-[16px] prose-h3:text-[14px]
          prose-p:text-[14px] prose-p:leading-[1.8] prose-p:text-slate-600
          prose-li:text-[14px] prose-li:text-slate-600 prose-li:leading-[1.7]
          prose-strong:text-slate-800 prose-strong:font-semibold
          prose-table:text-[13px]
          prose-th:bg-slate-50 prose-th:px-3 prose-th:py-2 prose-th:text-left prose-th:font-semibold prose-th:text-slate-700 prose-th:border-slate-200
          prose-td:px-3 prose-td:py-2 prose-td:border-slate-200 prose-td:text-slate-600
          prose-hr:border-slate-200/60
        ">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{cleaned}</ReactMarkdown>
        </div>
      </motion.div>
    </>
  )
}


/* ── Build next-step actions from diagnosis data ── */
function buildNextSteps(detail: StructuredDetail, navigate: ReturnType<typeof useNavigate>): NextStep[] {
  const gaps = detail.gap_skills ?? []
  const highPriGaps = gaps.filter(g => g.priority === 'high')
  const gapNames = (highPriGaps.length > 0 ? highPriGaps : gaps).slice(0, 3).map(g => g.skill).join('、')

  const goCoach = (prompt: string) => {
    navigate(-1)
    setTimeout(() => sendToCoach(prompt), 200)
  }

  return [
    {
      icon: <BookOpen className="w-4 h-4 text-emerald-500" />,
      label: '查看学习路径',
      desc: `${gaps.length} 项缺口技能的学习路线`,
      onClick: () => navigate('/profile/learning'),
    },
    {
      icon: <Target className="w-4 h-4 text-blue-500" />,
      label: '练缺口面试题',
      desc: gapNames ? `针对 ${gapNames} 出题` : '针对缺口技能出面试题',
      onClick: () => goCoach(
        gapNames
          ? `根据我的JD诊断缺口，帮我出几道关于 ${gapNames} 的面试题`
          : '根据上次JD诊断的缺口技能，帮我出几道相关面试题练练'
      ),
    },
    {
      icon: <Search className="w-4 h-4 text-indigo-500" />,
      label: '搜索类似岗位',
      desc: detail.jd_title ? `搜索更多${detail.jd_title}相关招聘` : '搜索类似的招聘岗位',
      onClick: () => goCoach(
        detail.jd_title
          ? `帮我搜索和「${detail.jd_title}」类似的其他招聘`
          : '帮我搜索和刚才诊断的JD类似的其他招聘'
      ),
    },
  ]
}

/* ═══════════════════════════════════════════════
   CoachResultPage — main component
   ═══════════════════════════════════════════════ */

export default function CoachResultPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery<CoachResultData>({
    queryKey: ['coach-result', id],
    queryFn: () => rawFetch(`/coach/results/${id}`),
    enabled: !!id,
  })

  const { data: history = [] } = useQuery<CoachResultItem[]>({
    queryKey: ['coach-results'],
    queryFn: () => rawFetch('/coach/results'),
  })

  const deleteMut = useMutation({
    mutationFn: (rid: number) => rawFetch(`/coach/results/${rid}`, { method: 'DELETE' }),
    onSuccess: (_data, rid) => {
      queryClient.invalidateQueries({ queryKey: ['coach-results'] })
      if (String(rid) === id) {
        const remaining = history.filter((h) => h.id !== rid)
        if (remaining.length > 0) navigate(`/coach/result/${remaining[0].id}`, { replace: true })
        else navigate('/', { replace: true })
      }
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="space-y-4 w-full max-w-[640px] px-6">
          {[1, 2, 3].map((i) => <div key={i} className="h-24 glass animate-pulse rounded-xl" />)}
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3">
        <p className="text-slate-500 text-[14px]">找不到这份分析结果</p>
        <button onClick={() => navigate(-1)} className="text-[var(--blue)] text-[13px] font-semibold cursor-pointer">返回</button>
      </div>
    )
  }

  const cfg = typeConfig[data.result_type] ?? typeConfig.general
  const isStructured = !!data.detail?._structured

  return (
    <div className="h-full overflow-y-auto flex">
      {/* ── History sidebar ── */}
      {history.length > 1 && (
        <div className="w-[220px] shrink-0 border-r border-white/30 overflow-y-auto hidden lg:block bg-white/20 backdrop-blur-sm">
          <div className="px-4 py-5">
            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-3">分析记录</p>
            <div className="space-y-1">
              {history.map((item) => {
                const itemCfg = typeConfig[item.result_type] ?? typeConfig.general
                const isActive = String(item.id) === id
                return (
                  <div
                    key={item.id}
                    className={`group relative px-3 py-2.5 rounded-lg transition-colors cursor-pointer ${
                      isActive ? 'bg-white shadow-sm border border-slate-200/80' : 'hover:bg-slate-50'
                    }`}
                    onClick={() => navigate(`/coach/result/${item.id}`)}
                  >
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className={`text-[10px] font-bold ${itemCfg.color}`}>{itemCfg.label}</span>
                      {item.metadata?.match_score != null && (
                        <span className="text-[10px] font-bold text-slate-500">{String(item.metadata.match_score)}%</span>
                      )}
                    </div>
                    <p className="text-[12px] text-slate-600 truncate pr-6">{item.title}</p>
                    <p className="text-[10px] text-slate-400 mt-0.5">{item.created_at?.slice(0, 10)}</p>
                    <button
                      onClick={(e) => { e.stopPropagation(); deleteMut.mutate(item.id) }}
                      className="absolute top-2.5 right-2 p-1 rounded text-slate-300 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all cursor-pointer"
                      title="删除"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* ── Main content ── */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-[680px] mx-auto px-6 py-8">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease }}
            className="mb-8"
          >
            <button
              onClick={() => navigate(-1)}
              className="flex items-center gap-1.5 text-[13px] text-slate-400 hover:text-slate-600 transition-colors cursor-pointer mb-5"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> 返回
            </button>
            <div className="flex items-center gap-2.5">
              <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${cfg.color} ${cfg.bg}`}>
                {cfg.label}
              </span>
              <span className="text-[11px] text-slate-400">{data.created_at?.slice(0, 10)}</span>
            </div>
          </motion.div>

          {/* Content — structured or fallback */}
          {isStructured
            ? <JDDiagnosisView detail={data.detail} nextSteps={buildNextSteps(data.detail, navigate)} />
            : <MarkdownView text={data.detail?.raw_text ?? ''} summary={data.summary} />
          }

          {/* Bottom actions */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4, duration: 0.3 }}
            className="mt-10 pt-6 border-t border-slate-200/60 flex items-center gap-3"
          >
            <button
              onClick={() => navigate(-1)}
              className="px-5 py-2.5 rounded-xl text-[13px] font-semibold text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
            >
              返回教练
            </button>
            <button
              onClick={() => navigate('/')}
              className="px-5 py-2.5 rounded-xl text-[13px] font-semibold text-[var(--blue)] bg-blue-50 hover:bg-blue-100 transition-colors cursor-pointer"
            >
              回到首页
            </button>
          </motion.div>
        </div>
      </div>
    </div>
  )
}
