/**
 * 投递详情页
 * 时间线：投递 → 各轮面试
 * 三级 AI：单题分析 / 单轮复盘 / 全程总结
 * 底部复盘区：手写 + AI 生成
 */
import { Fragment, useState, useRef, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Plus, Trash2, Sparkles, X, Loader2, Check } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

import {
  listApplications,
  updateApplicationStatus,
  deleteApplication,
  updateReflection,
} from '@/api/applications'
import {
  listInterviews,
  createInterview,
  analyzeInterview,
  deleteInterview,
} from '@/api/growthLog'
import type { InterviewRecord } from '@/api/growthLog'
import type { ApplicationStatus } from '@/types/application'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { sendToCoach } from '@/hooks/useCoachTrigger'

/* ─────────── constants ─────────── */

const STATUS_CFG: Record<string, { bg: string; label: string }> = {
  applied:     { bg: '#2563EB', label: '已投递' },
  screening:   { bg: '#7C3AED', label: '筛选中' },
  scheduled:   { bg: '#D97706', label: '已约面' },
  interviewed: { bg: '#EA580C', label: '已面试' },
  debriefed:   { bg: '#0891B2', label: '已复盘' },
  offer:       { bg: '#16A34A', label: 'Offer'  },
  rejected:    { bg: '#EF4444', label: '未通过' },
  withdrawn:   { bg: '#94A3B8', label: '已放弃' },
}

const PIPELINE = [
  { key: 'applied',     label: '投递' },
  { key: 'screening',   label: '筛选' },
  { key: 'scheduled',   label: '约面' },
  { key: 'interviewed', label: '面试' },
  { key: 'debriefed',   label: '复盘' },
]

const TERMINAL = ['offer', 'rejected', 'withdrawn'] as const

const ROUND_OPTIONS = ['笔试', '一面', '二面', '三面', 'HR面', '终面', '其他']

const SELF_RATING = [
  { key: 'good',   label: '发挥好', color: '#16A34A' },
  { key: 'medium', label: '正常',   color: '#D97706' },
  { key: 'bad',    label: '较差',   color: '#EF4444' },
]

const COLORS = ['#2563EB', '#7C3AED', '#0891B2', '#EA580C', '#16A34A', '#D97706']

/* ─────────── helpers ─────────── */

function fmtDate(iso: string) {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return '--'
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function fmtDay(dateStr: string) {
  // interview_at is YYYY-MM-DD; show as YYYY/M/D
  const [y, m, d] = dateStr.split('-')
  if (!y || !m || !d) return '--'
  return `${y}/${Number(m)}/${Number(d)}`
}

interface QAPair { q: string; a: string }

function parseQA(content: string): QAPair[] {
  const pairs: QAPair[] = []
  for (const block of content.split(/\n\n+/)) {
    const qm = block.match(/Q\d+:\s*([\s\S]+?)(?=\nA\d+:|$)/m)
    const am = block.match(/A\d+:\s*([\s\S]+?)$/m)
    if (qm) pairs.push({ q: qm[1].trim(), a: am ? am[1].trim() : '' })
  }
  return pairs.length > 0 ? pairs : content.trim() ? [{ q: content.trim(), a: '' }] : []
}

function serializeQA(pairs: QAPair[]): string {
  return pairs
    .filter(p => p.q.trim())
    .map((p, i) => `Q${i + 1}: ${p.q}\nA${i + 1}: ${p.a.trim() || '(未填写)'}`)
    .join('\n\n')
}

/* ─────────── PipelineStatus ─────────── */

function PipelineStatus({ status, onSelect }: {
  status: string
  onSelect: (s: ApplicationStatus) => void
}) {
  const [showOutcome, setShowOutcome] = useState(false)
  const isTerminal = (TERMINAL as readonly string[]).includes(status)
  const currentIdx = PIPELINE.findIndex(s => s.key === status)

  if (isTerminal) {
    const cfg = STATUS_CFG[status]
    return (
      <div className="flex items-center gap-2 mt-3">
        <span className="text-[11px] font-bold px-3 py-1 rounded-full text-white"
          style={{ background: cfg?.bg }}>
          {cfg?.label}
        </span>
        <button onClick={() => onSelect('debriefed' as ApplicationStatus)}
          className="text-[10px] text-slate-400 hover:text-slate-600 cursor-pointer transition-colors">
          撤销
        </button>
      </div>
    )
  }

  return (
    <div className="mt-3">
      <div className="flex items-center">
        {PIPELINE.map((step, i) => {
          const done    = i < currentIdx
          const current = i === currentIdx
          return (
            <Fragment key={step.key}>
              {i > 0 && (
                <div className="h-px flex-1 mx-1.5"
                  style={{ background: done ? '#93C5FD' : '#E2E8F0' }} />
              )}
              <button
                onClick={() => onSelect(step.key as ApplicationStatus)}
                className="flex flex-col items-center shrink-0 cursor-pointer"
              >
                <div className="w-3 h-3 rounded-full transition-all"
                  style={{
                    background: current ? '#2563EB' : done ? '#93C5FD' : '#E2E8F0',
                    boxShadow: current ? '0 0 0 3px rgba(37,99,235,0.18)' : 'none',
                  }} />
                <span className="text-[10px] mt-1 font-medium"
                  style={{ color: current ? '#2563EB' : done ? '#93C5FD' : '#CBD5E1' }}>
                  {step.label}
                </span>
              </button>
            </Fragment>
          )
        })}

        {/* Mark outcome trigger */}
        <div className="h-px w-3 mx-1.5" style={{ background: '#E2E8F0' }} />
        <button
          onClick={() => setShowOutcome(v => !v)}
          className="text-[10px] text-slate-400 hover:text-slate-600 cursor-pointer transition-colors shrink-0 pb-3.5"
        >
          标记结果
        </button>
      </div>

      {/* Outcome options — only visible after clicking */}
      {showOutcome && (
        <div className="flex items-center gap-1.5 mt-2 pl-0.5">
          {TERMINAL.map(key => (
            <button key={key}
              onClick={() => { onSelect(key as ApplicationStatus); setShowOutcome(false) }}
              className="text-[11px] font-medium px-2.5 py-1 rounded-lg border cursor-pointer transition-opacity hover:opacity-80"
              style={{
                color: STATUS_CFG[key].bg,
                borderColor: STATUS_CFG[key].bg + '40',
                background: STATUS_CFG[key].bg + '0d',
              }}>
              {STATUS_CFG[key].label}
            </button>
          ))}
          <button onClick={() => setShowOutcome(false)}
            className="text-[10px] text-slate-400 hover:text-slate-500 cursor-pointer ml-1 transition-colors">
            取消
          </button>
        </div>
      )}
    </div>
  )
}

/* ─────────── RoundCard ─────────── */

function RoundCard({ round, appId, idx }: {
  round: InterviewRecord
  appId: number
  idx: number
}) {
  const [analyzing, setAnalyzing] = useState(false)
  const [confirmDel, setConfirmDel] = useState(false)
  const qc = useQueryClient()

  const pairs   = parseQA(round.content_summary)
  const hasPairs = pairs.length > 0 && pairs[0].q
  const rating   = SELF_RATING.find(r => r.key === round.self_rating)
  const color    = COLORS[idx % COLORS.length]
  const dateLabel = round.interview_at ? fmtDay(round.interview_at) : fmtDate(round.created_at)

  const handleAnalyzeRound = async () => {
    setAnalyzing(true)
    try {
      await analyzeInterview(round.id)
      qc.invalidateQueries({ queryKey: ['pursuit-rounds', appId] })
    } finally { setAnalyzing(false) }
  }

  const handleAnalyzeQ = (q: string, a: string) =>
    sendToCoach(`帮我分析这道面试题的回答，指出亮点和不足，并给出改进建议：\n\n题目：${q}\n\n我的回答：${a || '（未填写）'}`)

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: idx * 0.05, duration: 0.28 }}
        className="relative flex items-start gap-0 mb-6"
      >
        {/* Dot + date */}
        <div className="flex flex-col items-center shrink-0 w-14 pt-1 z-10">
          <div className="w-3.5 h-3.5 rounded-full border-2 border-white shadow-sm"
            style={{ background: color }} />
          <span className="text-[9px] text-slate-400 mt-1 tabular-nums text-center leading-tight">
            {dateLabel}
          </span>
        </div>

        {/* Card */}
        <div className="flex-1 group glass-static rounded-xl px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[13px] font-bold text-slate-800">{round.round}</span>
              {rating && (
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                  style={{ background: rating.color + '18', color: rating.color }}>
                  {rating.label}
                </span>
              )}
              {round.result !== 'pending' && (
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                  style={{
                    background: round.result === 'passed' ? 'rgba(22,163,74,0.1)' : 'rgba(239,68,68,0.1)',
                    color:      round.result === 'passed' ? '#16A34A' : '#EF4444',
                  }}>
                  {round.result === 'passed' ? '通过' : '未通过'}
                </span>
              )}
            </div>
            {/* Hover actions */}
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button onClick={handleAnalyzeRound} disabled={analyzing}
                className="p-1 rounded text-slate-400 hover:text-purple-500 hover:bg-purple-50 transition-colors cursor-pointer"
                title="AI 复盘本轮">
                {analyzing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
              </button>
              <button onClick={() => setConfirmDel(true)}
                className="p-1 rounded text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors cursor-pointer">
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          </div>

          {/* Q/A */}
          {hasPairs && (
            <div className="space-y-2 mt-2.5">
              {pairs.map((pair, i) => (
                <div key={i}>
                  <div className="flex items-start gap-1.5">
                    <span className="text-[10px] font-bold text-blue-500 mt-0.5 shrink-0 w-5">Q{i + 1}</span>
                    <p className="text-[12px] font-medium text-slate-800 leading-relaxed flex-1">{pair.q}</p>
                    <button
                      onClick={() => handleAnalyzeQ(pair.q, pair.a)}
                      className="shrink-0 p-0.5 text-slate-300 hover:text-purple-500 transition-colors cursor-pointer"
                      title="AI 分析这道题">
                      <Sparkles className="w-2.5 h-2.5" />
                    </button>
                  </div>
                  {pair.a && pair.a !== '(未填写)' && (
                    <div className="flex items-start gap-1.5 pl-5 mt-0.5">
                      <span className="text-[10px] font-bold text-slate-300 mt-0.5 shrink-0 w-5">A{i + 1}</span>
                      <p className="text-[11px] text-slate-500 leading-relaxed">{pair.a}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* AI analysis result */}
          {round.ai_analysis && (
            <div className="mt-3 p-3 rounded-lg"
              style={{ background: 'rgba(8,145,178,0.05)', border: '1px solid rgba(8,145,178,0.12)' }}>
              <p className="text-[10px] font-bold text-cyan-600 mb-1">AI 复盘</p>
              {round.ai_analysis.overall && (
                <p className="text-[11px] text-slate-700 leading-relaxed mb-1">{round.ai_analysis.overall}</p>
              )}
              {round.ai_analysis.strengths?.length > 0 && (
                <p className="text-[10px] text-slate-600">
                  <span className="font-semibold text-emerald-600">亮点：</span>
                  {round.ai_analysis.strengths.join('；')}
                </p>
              )}
              {round.ai_analysis.weaknesses?.length > 0 && (
                <p className="text-[10px] text-slate-600 mt-0.5">
                  <span className="font-semibold text-amber-600">改进：</span>
                  {round.ai_analysis.weaknesses.join('；')}
                </p>
              )}
              {round.ai_analysis.action_items?.length > 0 && (
                <p className="text-[10px] text-slate-600 mt-0.5">
                  <span className="font-semibold text-blue-600">建议：</span>
                  {round.ai_analysis.action_items.join('；')}
                </p>
              )}
            </div>
          )}
        </div>
      </motion.div>

      <AnimatePresence>
        {confirmDel && (
          <ConfirmDialog
            message={`删除「${round.round}」的面试记录？`}
            onConfirm={async () => {
              setConfirmDel(false)
              await deleteInterview(round.id)
              qc.invalidateQueries({ queryKey: ['pursuit-rounds', appId] })
            }}
            onCancel={() => setConfirmDel(false)}
          />
        )}
      </AnimatePresence>
    </>
  )
}

/* ─────────── AddInterviewForm ─────────── */

function AddInterviewForm({ appId, company, position, onClose }: {
  appId: number
  company: string
  position: string
  onClose: () => void
}) {
  const [round, setRound]     = useState('一面')
  const [date, setDate]       = useState(new Date().toISOString().split('T')[0])
  const [selfRating, setSelf] = useState('medium')
  const [pairs, setPairs]     = useState<QAPair[]>([{ q: '', a: '' }])
  const qc = useQueryClient()

  const { mutate: save, isPending } = useMutation({
    mutationFn: () => createInterview({
      company, position, round,
      content_summary: serializeQA(pairs),
      self_rating: selfRating as 'good' | 'medium' | 'bad',
      result: 'pending',
      interview_at: date || undefined,
      application_id: appId,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['pursuit-rounds', appId] }); onClose() },
  })

  const updatePair = (i: number, f: 'q' | 'a', v: string) =>
    setPairs(pairs.map((p, idx) => idx === i ? { ...p, [f]: v } : p))

  const iCls = "w-full px-3.5 py-2.5 text-[12px] rounded-xl outline-none bg-slate-50 border border-slate-200 focus:border-blue-400 focus:bg-white transition-colors"

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" onClick={onClose} />
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.96 }}
        className="relative bg-white rounded-2xl p-6 w-full max-w-[480px] shadow-xl z-10 max-h-[88vh] overflow-y-auto"
      >
        <p className="text-[15px] font-bold text-slate-800 mb-5">记录面试</p>
        <div className="space-y-4">

          {/* Round type */}
          <div>
            <p className="text-[11px] text-slate-400 mb-1.5">轮次</p>
            <div className="flex flex-wrap gap-1.5">
              {ROUND_OPTIONS.map(r => (
                <button key={r} type="button" onClick={() => setRound(r)}
                  className="px-2.5 py-1 rounded-lg text-[11px] font-medium cursor-pointer transition-all border"
                  style={{
                    background:   round === r ? '#2563EB' : 'transparent',
                    color:        round === r ? '#fff' : '#94A3B8',
                    borderColor:  round === r ? '#2563EB' : 'rgba(0,0,0,0.1)',
                  }}>
                  {r}
                </button>
              ))}
            </div>
          </div>

          {/* Date + self-rating */}
          <div className="flex gap-4 items-start">
            <div>
              <p className="text-[11px] text-slate-400 mb-1.5">面试日期</p>
              <input type="date" value={date} onChange={e => setDate(e.target.value)}
                className="px-3 py-2 text-[12px] rounded-xl border border-slate-200 bg-slate-50 outline-none focus:border-blue-400 cursor-pointer" />
            </div>
            <div>
              <p className="text-[11px] text-slate-400 mb-1.5">发挥</p>
              <div className="flex gap-1.5">
                {SELF_RATING.map(r => (
                  <button key={r.key} type="button" onClick={() => setSelf(r.key)}
                    className="px-2.5 py-1 rounded-lg text-[11px] font-medium cursor-pointer transition-all border"
                    style={{
                      background:  selfRating === r.key ? r.color + '18' : 'transparent',
                      color:       selfRating === r.key ? r.color : '#94A3B8',
                      borderColor: selfRating === r.key ? r.color + '50' : 'rgba(0,0,0,0.1)',
                    }}>
                    {r.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Q/A */}
          <div>
            <p className="text-[11px] text-slate-400 mb-2">面试题目（选填）</p>
            <div className="space-y-3">
              {pairs.map((pair, i) => (
                <div key={i} className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold text-blue-500 w-5 shrink-0">Q{i + 1}</span>
                    <input value={pair.q} onChange={e => updatePair(i, 'q', e.target.value)}
                      placeholder="面试题目" className={iCls} />
                    {pairs.length > 1 && (
                      <button onClick={() => setPairs(pairs.filter((_, idx) => idx !== i))}
                        className="p-1 text-slate-300 hover:text-red-400 cursor-pointer transition-colors">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                  <div className="pl-7">
                    <textarea value={pair.a} onChange={e => updatePair(i, 'a', e.target.value)}
                      placeholder="我的回答要点（可选）" rows={2}
                      className={iCls + ' resize-none'} />
                  </div>
                </div>
              ))}
            </div>
            <button onClick={() => setPairs([...pairs, { q: '', a: '' }])}
              className="flex items-center gap-1 text-[11px] text-blue-500 hover:text-blue-700 cursor-pointer mt-2 transition-colors">
              <Plus className="w-3 h-3" /> 再加一题
            </button>
          </div>

          <div className="flex gap-2 pt-1">
            <button onClick={() => save()} disabled={isPending}
              className="flex-1 py-2.5 text-[13px] font-semibold text-white rounded-xl cursor-pointer disabled:opacity-50"
              style={{ background: '#2563EB' }}>
              {isPending ? '保存中...' : '保存'}
            </button>
            <button onClick={onClose}
              className="px-4 py-2.5 text-[13px] text-slate-500 rounded-xl cursor-pointer border border-slate-200 hover:bg-slate-50 transition-colors">
              取消
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

/* ─────────── ReflectionSection ─────────── */

function ReflectionSection({ appId, initial, rounds }: {
  appId: number
  initial: string | null
  rounds: InterviewRecord[]
}) {
  const [text, setText] = useState(initial ?? '')
  const [saved, setSaved] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // autosave with debounce
  const handleChange = (v: string) => {
    setText(v)
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(async () => {
      await updateReflection(appId, v)
      setSaved(true)
      setTimeout(() => setSaved(false), 1500)
    }, 800)
  }

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current) }, [])

  const handleAI = () => {
    const roundSummary = rounds.slice(0, 3).map((r, i) => {
      const pairs = parseQA(r.content_summary)
      const qa = pairs.filter(p => p.q).map((p, j) =>
        `  Q${j + 1}: ${p.q}${p.a && p.a !== '(未填写)' ? `\n  A${j + 1}: ${p.a}` : ''}`
      ).join('\n')
      const rating = SELF_RATING.find(s => s.key === r.self_rating)?.label ?? ''
      return `【${r.round}】${rating ? ' · ' + rating : ''}\n${qa || '（无题目记录）'}`
    }).join('\n\n')

    sendToCoach(
      `请帮我全面复盘这段求职经历，总结不足之处并给出具体提升建议：\n\n` +
      `面试记录：\n${roundSummary}\n\n` +
      `我的感受：\n${text || '（未填写）'}\n\n` +
      `请从以下角度分析：\n` +
      `1. 整体表现评估\n2. 每轮的关键失误或不足\n3. 技术/表达/心态各维度的具体改进方向\n4. 下次面试这类岗位重点准备什么`
    )
  }

  return (
    <div className="mt-6">
      <div className="flex items-center gap-3 mb-4">
        <span className="text-[13px] font-semibold text-slate-600">整体复盘</span>
        <div className="flex-1 h-px bg-slate-200/60" />
        {saved && (
          <span className="flex items-center gap-1 text-[10px] text-emerald-500">
            <Check className="w-3 h-3" /> 已保存
          </span>
        )}
      </div>

      <textarea
        value={text}
        onChange={e => handleChange(e.target.value)}
        placeholder="记录这段经历的感受、收获、遗憾...（自动保存）"
        rows={4}
        className="w-full px-4 py-3 text-[13px] rounded-2xl outline-none bg-white/60 border border-slate-200 focus:border-blue-400 focus:bg-white transition-colors resize-none leading-relaxed text-slate-700 placeholder:text-slate-300"
      />

      <button
        onClick={handleAI}
        className="w-full mt-3 flex items-center justify-center gap-2 py-2.5 text-[12px] font-semibold rounded-xl cursor-pointer transition-opacity hover:opacity-80"
        style={{
          background: 'linear-gradient(135deg, rgba(37,99,235,0.07), rgba(124,58,237,0.07))',
          color: '#2563EB',
          border: '1px solid rgba(37,99,235,0.15)',
        }}>
        <Sparkles className="w-3.5 h-3.5 text-purple-500" />
        AI 帮我复盘全程，总结不足与提升方向
      </button>
    </div>
  )
}

/* ─────────── Main Page ─────────── */

export default function PursuitDetailPage() {
  const { id }   = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc       = useQueryClient()
  const appId    = Number(id)

  const [showAdd, setShowAdd]           = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const { data: apps = [] } = useQuery({
    queryKey: ['pursuits-apps'],
    queryFn: listApplications,
    staleTime: 60_000,
  })
  const app = apps.find(a => a.id === appId)

  const { data: ivData, isLoading } = useQuery({
    queryKey: ['pursuit-rounds', appId],
    queryFn: listInterviews,
    enabled: Number.isFinite(appId),
    staleTime: 0,
  })
  const rounds = (ivData?.interviews ?? [])
    .filter(iv => iv.application_id === appId)
    .sort((a, b) =>
      new Date(a.interview_at || a.created_at).getTime() -
      new Date(b.interview_at || b.created_at).getTime()
    )

  const handleStatusChange = async (s: ApplicationStatus) => {
    await updateApplicationStatus(appId, s)
    qc.invalidateQueries({ queryKey: ['pursuits-apps'] })
  }

  const handleDeleteApp = async () => {
    setConfirmDelete(false)
    await deleteApplication(appId)
    qc.invalidateQueries({ queryKey: ['pursuits-apps'] })
    navigate('/growth-log')
  }

  if (!Number.isFinite(appId)) {
    return (
      <div className="max-w-[720px] mx-auto px-4 py-6 md:px-8 text-center">
        <p className="text-slate-500 mb-4">无效的投递 ID</p>
        <button onClick={() => navigate('/growth-log')} className="text-[var(--blue)] font-medium cursor-pointer">
          返回成长档案
        </button>
      </div>
    )
  }

  if (!app) return null

  return (
    <div className="max-w-[720px] mx-auto px-4 py-6 md:px-8">

      {/* ── Header ── */}
      <div className="flex items-start gap-3 mb-5">
        <button onClick={() => navigate('/growth-log')}
          className="p-1.5 rounded-lg hover:bg-white/40 transition-colors cursor-pointer text-slate-400 hover:text-slate-700 mt-1">
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="flex-1 min-w-0">
          <p className="text-[20px] font-bold text-slate-900 truncate">{app.company || '未知公司'}</p>
          <p className="text-[13px] text-slate-500 mt-0.5 truncate">{app.position || '未命名岗位'}</p>
          <PipelineStatus status={app.status} onSelect={handleStatusChange} />
        </div>
        <button onClick={() => setShowAdd(true)}
          className="flex items-center gap-1.5 px-4 py-2 bg-slate-800 text-white rounded-xl text-[12px] font-semibold hover:bg-slate-700 transition-colors cursor-pointer shrink-0 mt-1">
          <Plus className="w-3.5 h-3.5" /> 记录面试
        </button>
      </div>

      {/* ── Timeline ── */}
      <div className="relative">
        {rounds.length > 0 && (
          <div className="absolute left-7 top-4 bottom-4 w-0.5 bg-slate-200" />
        )}

        {/* Application start node */}
        <div className="relative flex items-start gap-0 mb-6">
          <div className="flex flex-col items-center shrink-0 w-14 pt-1 z-10">
            <div className="w-3.5 h-3.5 rounded-full border-2 border-white shadow-sm bg-slate-300" />
            <span className="text-[9px] text-slate-400 mt-1 tabular-nums text-center leading-tight">
              {fmtDate(app.created_at)}
            </span>
          </div>
          <div className="flex-1 glass-static rounded-xl px-4 py-3">
            <span className="text-[12px] font-semibold text-slate-700">投递记录</span>
            {app.notes && <p className="text-[11px] text-slate-400 mt-1">{app.notes}</p>}
          </div>
        </div>

        {/* Interview rounds */}
        {isLoading ? (
          <div className="space-y-4 pl-14">
            {[1, 2].map(i => <div key={i} className="h-20 glass-static animate-pulse rounded-xl" />)}
          </div>
        ) : rounds.length === 0 ? (
          <div className="relative flex items-start gap-0 mb-2">
            <div className="shrink-0 w-14 flex justify-center pt-1.5 z-10">
              <div className="w-3 h-3 rounded-full border-2 border-dashed border-slate-300" />
            </div>
            <button onClick={() => setShowAdd(true)}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-[12px] font-semibold cursor-pointer border transition-colors"
              style={{ color: '#2563EB', borderColor: 'rgba(37,99,235,0.2)', background: 'rgba(37,99,235,0.04)' }}>
              <Plus className="w-3.5 h-3.5" /> 记录第一轮面试
            </button>
          </div>
        ) : (
          <>
            {rounds.map((r, i) => <RoundCard key={r.id} round={r} appId={appId} idx={i} />)}
            {/* Inline add-more button at end of timeline */}
            <div className="relative flex items-start gap-0 mb-2">
              <div className="shrink-0 w-14 flex justify-center pt-1.5 z-10">
                <div className="w-3 h-3 rounded-full border-2 border-dashed border-slate-300" />
              </div>
              <button onClick={() => setShowAdd(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[12px] font-medium cursor-pointer border transition-colors hover:bg-blue-50"
                style={{ color: '#2563EB', borderColor: 'rgba(37,99,235,0.2)', background: 'rgba(37,99,235,0.03)' }}>
                <Plus className="w-3.5 h-3.5" /> 继续添加下一轮
              </button>
            </div>
          </>
        )}
      </div>

      {/* ── Retrospective — only after application is concluded ── */}
      {(TERMINAL as readonly string[]).includes(app.status) && (
        <ReflectionSection appId={appId} initial={app.reflection ?? null} rounds={rounds} />
      )}

      {/* ── Delete ── */}
      <div className="mt-4 flex justify-center">
        <button onClick={() => setConfirmDelete(true)}
          className="text-[11px] text-slate-400 hover:text-red-500 cursor-pointer transition-colors px-3 py-1.5 rounded-lg hover:bg-red-50">
          删除这条投递记录
        </button>
      </div>

      {/* ── Modals ── */}
      <AnimatePresence>
        {showAdd && (
          <AddInterviewForm
            appId={appId}
            company={app.company ?? ''}
            position={app.position ?? ''}
            onClose={() => setShowAdd(false)}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {confirmDelete && (
          <ConfirmDialog
            message={`删除「${app.company}」的投递及所有面试记录？`}
            onConfirm={handleDeleteApp}
            onCancel={() => setConfirmDelete(false)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
