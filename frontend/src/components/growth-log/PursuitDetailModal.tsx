/**
 * 实战经历详情 Modal
 * - 管道状态切换（点击直接跳转）
 * - 面试轮次 Q/A 结构化记录
 * - 三粒度 AI 复盘：单题 / 单轮 / 全部
 */
import { useState, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X, Plus, ChevronDown, ChevronUp,
  Sparkles, Trash2, Check, Loader2,
} from 'lucide-react'
import { listApplications, updateApplicationStatus, deleteApplication } from '@/api/applications'
import { listInterviews, createInterview, analyzeInterview, deleteInterview } from '@/api/growthLog'
import { sendToCoach } from '@/hooks/useCoachTrigger'
import type { ApplicationStatus } from '@/types/application'
import type { InterviewRecord } from '@/api/growthLog'

/* ── Constants ── */

const APP_STATUS: Record<string, { label: string; color: string; bg: string }> = {
  applied:     { label: '已投递', color: '#2563EB', bg: 'rgba(37,99,235,0.10)'  },
  screening:   { label: '筛选中', color: '#7C3AED', bg: 'rgba(124,58,237,0.10)' },
  scheduled:   { label: '已约面', color: '#D97706', bg: 'rgba(217,119,6,0.10)'  },
  interviewed: { label: '已面试', color: '#EA580C', bg: 'rgba(234,88,12,0.10)'  },
  debriefed:   { label: '已复盘', color: '#0891B2', bg: 'rgba(8,145,178,0.10)'  },
  offer:       { label: 'Offer',  color: '#16A34A', bg: 'rgba(22,163,74,0.10)'  },
  rejected:    { label: '未通过', color: '#EF4444', bg: 'rgba(239,68,68,0.10)'  },
  withdrawn:   { label: '已放弃', color: '#8E8E93', bg: 'rgba(142,142,147,0.12)'},
}

const PIPELINE = [
  { key: 'applied',     label: '投递' },
  { key: 'screening',   label: '筛选' },
  { key: 'scheduled',   label: '约面' },
  { key: 'interviewed', label: '面试' },
  { key: 'debriefed',   label: '复盘' },
]
const TERMINAL = ['offer', 'rejected', 'withdrawn']
const ROUND_OPTIONS = ['笔试', '一面', '二面', '三面', 'HR面', '终面', '其他']
const SELF_RATING = [
  { key: 'good',   label: '发挥好', color: '#16A34A' },
  { key: 'medium', label: '正常',   color: '#D97706' },
  { key: 'bad',    label: '较差',   color: '#EF4444' },
]

function todayStr() {
  return new Date().toISOString().split('T')[0]
}

function fmtDate(iso: string | null) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

/* ── Q/A helpers ── */

interface QAPair { q: string; a: string }

function parseQA(content: string): QAPair[] {
  const pairs: QAPair[] = []
  const blocks = content.split(/\n\n+/)
  for (const block of blocks) {
    const qm = block.match(/Q\d+:\s*([\s\S]+?)(?=\nA\d+:|$)/m)
    const am = block.match(/A\d+:\s*([\s\S]+?)$/m)
    if (qm) pairs.push({ q: qm[1].trim(), a: am ? am[1].trim() : '' })
  }
  if (pairs.length === 0 && content.trim()) {
    pairs.push({ q: content.trim(), a: '' })
  }
  return pairs
}

function serializeQA(pairs: QAPair[]): string {
  return pairs
    .filter(p => p.q.trim())
    .map((p, i) => `Q${i + 1}: ${p.q}\nA${i + 1}: ${p.a.trim() || '(未填写)'}`)
    .join('\n\n')
}

/* ── Status Selector — same pill style as ProjectDetailModal ── */
const STATUS_ROWS = [
  [
    { key: 'applied',     label: '已投递' },
    { key: 'screening',   label: '筛选中' },
    { key: 'scheduled',   label: '已约面' },
    { key: 'interviewed', label: '已面试' },
    { key: 'debriefed',   label: '已复盘' },
  ],
  [
    { key: 'offer',     label: 'Offer'  },
    { key: 'rejected',  label: '未通过' },
    { key: 'withdrawn', label: '已放弃' },
  ],
]

function StatusSelector({ status, onSelect, disabled }: {
  status: string
  onSelect: (s: ApplicationStatus) => void
  disabled?: boolean
}) {
  return (
    <div className="mt-3 space-y-2">
      <div className="flex flex-wrap gap-1.5">
        {STATUS_ROWS[0].map(s => {
          const st = APP_STATUS[s.key]
          const active = status === s.key
          return (
            <button key={s.key}
              onClick={() => !disabled && onSelect(s.key as ApplicationStatus)}
              className="px-3 py-1 text-[10px] font-semibold rounded-[20px] cursor-pointer transition-all"
              style={{
                background: active ? st.bg : 'rgba(0,0,0,0.04)',
                color: active ? st.color : '#C7C7CC',
                border: active ? `1.5px solid ${st.color}33` : '1.5px solid transparent',
              }}>
              {s.label}
            </button>
          )
        })}
        {/* divider */}
        <div className="w-px self-stretch mx-0.5" style={{ background: 'rgba(0,0,0,0.08)' }} />
        {STATUS_ROWS[1].map(s => {
          const st = APP_STATUS[s.key]
          const active = status === s.key
          return (
            <button key={s.key}
              onClick={() => !disabled && onSelect(s.key as ApplicationStatus)}
              className="px-3 py-1 text-[10px] font-semibold rounded-[20px] cursor-pointer transition-all"
              style={{
                background: active ? st.bg : 'rgba(0,0,0,0.04)',
                color: active ? st.color : '#C7C7CC',
                border: active ? `1.5px solid ${st.color}33` : '1.5px solid transparent',
              }}>
              {s.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

/* ── Add Round Form ── */
function AddRoundForm({ applicationId, company, position, onSuccess, onCancel }: {
  applicationId: number
  company: string
  position: string
  onSuccess: () => void
  onCancel: () => void
}) {
  const [round, setRound]         = useState('一面')
  const [date, setDate]           = useState(todayStr())
  const [selfRating, setSelf]     = useState('medium')
  const [pairs, setPairs]         = useState<QAPair[]>([{ q: '', a: '' }])
  const [saving, setSaving]       = useState(false)
  const [error, setError]         = useState('')

  function updatePair(i: number, field: 'q' | 'a', val: string) {
    setPairs(pairs.map((p, idx) => idx === i ? { ...p, [field]: val } : p))
  }

  async function handleSave() {
    const valid = pairs.filter(p => p.q.trim())
    if (valid.length === 0) { setError('至少填写一道题目'); return }
    setSaving(true); setError('')
    try {
      await createInterview({
        company, position,
        round,
        content_summary: serializeQA(valid),
        self_rating: selfRating,
        result: 'pending',
        interview_at: date || undefined,
        application_id: applicationId,
      })
      onSuccess()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '保存失败')
    } finally { setSaving(false) }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      className="rounded-[16px] p-4 space-y-3"
      style={{ background: 'rgba(37,99,235,0.03)', border: '1px solid rgba(37,99,235,0.12)' }}
    >
      {/* Round meta */}
      <div className="flex items-center gap-2 flex-wrap">
        <select value={round} onChange={e => setRound(e.target.value)}
          className="px-2.5 py-1.5 text-[11px] rounded-[8px] outline-none cursor-pointer"
          style={{ background: 'rgba(0,0,0,0.04)', border: '1px solid rgba(0,0,0,0.08)', color: '#1a1a1a' }}>
          {ROUND_OPTIONS.map(r => <option key={r} value={r}>{r}</option>)}
        </select>
        <input type="date" value={date} onChange={e => setDate(e.target.value)}
          className="px-2.5 py-1.5 text-[11px] rounded-[8px] outline-none"
          style={{ background: 'rgba(0,0,0,0.04)', border: '1px solid rgba(0,0,0,0.08)', color: '#1a1a1a' }} />
        <div className="flex gap-1">
          {SELF_RATING.map(r => (
            <button key={r.key} onClick={() => setSelf(r.key)}
              className="px-2.5 py-1 text-[10px] font-semibold rounded-[6px] cursor-pointer transition-all"
              style={{
                background: selfRating === r.key ? `${r.color}15` : 'rgba(0,0,0,0.04)',
                color: selfRating === r.key ? r.color : '#8E8E93',
                border: selfRating === r.key ? `1px solid ${r.color}40` : '1px solid transparent',
              }}>
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Q/A pairs */}
      <div className="space-y-3">
        {pairs.map((pair, i) => (
          <div key={i} className="space-y-1.5">
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] font-bold text-[#2563EB] w-5 shrink-0">Q{i + 1}</span>
              <input value={pair.q} onChange={e => updatePair(i, 'q', e.target.value)}
                placeholder="面试题目"
                className="flex-1 px-2.5 py-1.5 text-[11px] rounded-[8px] outline-none"
                style={{ background: '#fff', border: '1px solid rgba(0,0,0,0.08)', color: '#1a1a1a' }}
                onFocus={e => (e.currentTarget.style.border = '1px solid rgba(37,99,235,0.4)')}
                onBlur={e => (e.currentTarget.style.border = '1px solid rgba(0,0,0,0.08)')}
              />
              {pairs.length > 1 && (
                <button onClick={() => setPairs(pairs.filter((_, idx) => idx !== i))}
                  className="p-1 text-[#C7C7CC] hover:text-red-400 cursor-pointer transition-colors">
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
            <div className="flex items-start gap-1.5 pl-6">
              <span className="text-[10px] font-bold text-[#8E8E93] w-5 shrink-0 mt-1.5">A{i + 1}</span>
              <textarea value={pair.a} onChange={e => updatePair(i, 'a', e.target.value)}
                placeholder="我的回答（可简要记录要点）"
                rows={2}
                className="flex-1 px-2.5 py-1.5 text-[11px] rounded-[8px] outline-none resize-none"
                style={{ background: '#fff', border: '1px solid rgba(0,0,0,0.08)', color: '#1a1a1a' }}
                onFocus={e => (e.currentTarget.style.border = '1px solid rgba(37,99,235,0.4)')}
                onBlur={e => (e.currentTarget.style.border = '1px solid rgba(0,0,0,0.08)')}
              />
            </div>
          </div>
        ))}
      </div>

      <button onClick={() => setPairs([...pairs, { q: '', a: '' }])}
        className="flex items-center gap-1 text-[10px] font-medium cursor-pointer"
        style={{ color: '#2563EB' }}>
        <Plus className="w-3 h-3" /> 再加一题
      </button>

      {error && <p className="text-[10px] text-red-500">{error}</p>}

      <div className="flex gap-2 pt-1">
        <button onClick={handleSave} disabled={saving}
          className="flex items-center gap-1.5 px-4 py-2 text-[11px] font-semibold text-white rounded-[9px] cursor-pointer disabled:opacity-50"
          style={{ background: '#2563EB' }}>
          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
          {saving ? '保存中...' : '保存本轮'}
        </button>
        <button onClick={onCancel}
          className="px-4 py-2 text-[11px] text-[#8E8E93] rounded-[9px] cursor-pointer"
          style={{ background: 'rgba(0,0,0,0.04)' }}>
          取消
        </button>
      </div>
    </motion.div>
  )
}

/* ── Round Card ── */
function RoundCard({ round, expanded, onToggle, onAnalyzeRound, onAnalyzeQ, analyzing }: {
  round: InterviewRecord
  expanded: boolean
  onToggle: () => void
  onAnalyzeRound: () => void
  onAnalyzeQ: (q: string, a: string) => void
  analyzing: boolean
}) {
  const pairs = parseQA(round.content_summary)
  const ratingInfo = SELF_RATING.find(r => r.key === round.self_rating)

  return (
    <div className="rounded-[14px] overflow-hidden"
      style={{ border: '1px solid rgba(0,0,0,0.06)' }}>
      {/* Round header */}
      <button onClick={onToggle}
        className="w-full flex items-center justify-between px-4 py-3 cursor-pointer transition-colors"
        style={{ background: expanded ? 'rgba(37,99,235,0.03)' : '#FAFAFA' }}>
        <div className="flex items-center gap-2.5">
          <span className="text-[13px] font-bold text-[#1a1a1a]">{round.round}</span>
          {ratingInfo && (
            <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-[4px]"
              style={{ background: `${ratingInfo.color}12`, color: ratingInfo.color }}>
              {ratingInfo.label}
            </span>
          )}
          {round.result !== 'pending' && (
            <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-[4px]"
              style={{
                background: round.result === 'passed' ? 'rgba(22,163,74,0.1)' : 'rgba(239,68,68,0.1)',
                color: round.result === 'passed' ? '#16A34A' : '#EF4444',
              }}>
              {round.result === 'passed' ? '通过' : '未通过'}
            </span>
          )}
          <span className="text-[10px] text-[#C7C7CC]">
            {fmtDate(round.interview_at || round.created_at)}
          </span>
          <span className="text-[10px] text-[#C7C7CC]">{pairs.length} 题</span>
        </div>
        {expanded
          ? <ChevronUp className="w-3.5 h-3.5 text-[#C7C7CC]" />
          : <ChevronDown className="w-3.5 h-3.5 text-[#C7C7CC]" />
        }
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-4 pb-4 space-y-3">
          {/* Q/A list */}
          {pairs.map((pair, i) => (
            <div key={i} className="space-y-1">
              <div className="flex items-start gap-2">
                <span className="text-[10px] font-bold text-[#2563EB] mt-0.5 shrink-0">Q{i + 1}</span>
                <p className="text-[12px] font-medium text-[#1a1a1a] flex-1 leading-relaxed">{pair.q}</p>
                {/* Single Q AI button */}
                <button
                  onClick={() => onAnalyzeQ(pair.q, pair.a)}
                  className="shrink-0 flex items-center gap-1 px-2 py-1 rounded-[6px] text-[9px] font-semibold cursor-pointer transition-all"
                  style={{ background: 'rgba(124,58,237,0.08)', color: '#7C3AED' }}
                  title="让 AI 分析这道题的回答">
                  <Sparkles className="w-2.5 h-2.5" /> 单题
                </button>
              </div>
              {pair.a && pair.a !== '(未填写)' && (
                <div className="pl-5">
                  <span className="text-[10px] font-bold text-[#8E8E93] mr-1.5">A{i + 1}</span>
                  <span className="text-[11px] text-[#636366] leading-relaxed">{pair.a}</span>
                </div>
              )}
            </div>
          ))}

          {/* AI analysis result */}
          {round.ai_analysis && (
            <div className="mt-3 p-3 rounded-[10px] space-y-1.5"
              style={{ background: 'rgba(8,145,178,0.05)', border: '1px solid rgba(8,145,178,0.12)' }}>
              <p className="text-[10px] font-bold" style={{ color: '#0891B2' }}>AI 复盘</p>
              {round.ai_analysis.overall && (
                <p className="text-[11px] font-medium text-[#1a1a1a]">{round.ai_analysis.overall}</p>
              )}
              {round.ai_analysis.strengths?.length > 0 && (
                <p className="text-[10px] text-[#374151]">
                  <span className="font-semibold text-emerald-600">亮点：</span>
                  {round.ai_analysis.strengths.join('；')}
                </p>
              )}
              {round.ai_analysis.weaknesses?.length > 0 && (
                <p className="text-[10px] text-[#374151]">
                  <span className="font-semibold text-amber-600">改进：</span>
                  {round.ai_analysis.weaknesses.join('；')}
                </p>
              )}
              {round.ai_analysis.action_items?.length > 0 && (
                <p className="text-[10px] text-[#374151]">
                  <span className="font-semibold" style={{ color: '#2563EB' }}>建议：</span>
                  {round.ai_analysis.action_items.join('；')}
                </p>
              )}
            </div>
          )}

          {/* Analyze round button */}
          <button onClick={onAnalyzeRound} disabled={analyzing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-semibold rounded-[8px] cursor-pointer disabled:opacity-50 transition-all mt-2"
            style={{
              background: round.ai_analysis ? 'rgba(8,145,178,0.06)' : 'rgba(37,99,235,0.08)',
              color: round.ai_analysis ? '#0891B2' : '#2563EB',
            }}>
            {analyzing
              ? <><Loader2 className="w-3 h-3 animate-spin" /> 分析中...</>
              : <><Sparkles className="w-3 h-3" /> {round.ai_analysis ? '重新分析本轮' : '分析本轮'}</>
            }
          </button>
        </div>
      )}
    </div>
  )
}

/* ── Main Modal ── */
export function PursuitDetailModal({ appId, onClose, onRefresh }: {
  appId: number
  onClose: () => void
  onRefresh: () => void
}) {
  const qc = useQueryClient()

  const { data: apps = [] } = useQuery({
    queryKey: ['pursuits-apps'],
    queryFn: listApplications,
    staleTime: 3 * 60_000,
  })
  const { data: ivData, refetch: refetchRounds } = useQuery({
    queryKey: ['pursuit-rounds', appId],
    queryFn: listInterviews,
    staleTime: 0,
  })

  const app = apps.find(a => a.id === appId)
  const rounds = (ivData?.interviews ?? [])
    .filter(iv => iv.application_id === appId)
    .sort((a, b) => new Date(a.interview_at || a.created_at).getTime() - new Date(b.interview_at || b.created_at).getTime())

  const [status, setStatus]           = useState(app?.status ?? 'applied')
  const [statusSaving, setStatusSaving] = useState(false)
  const [addingRound, setAddingRound] = useState(false)
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set(rounds.map(r => r.id)))
  const [analyzingId, setAnalyzingId] = useState<number | null>(null)
  const [analyzingAll, setAnalyzingAll] = useState(false)
  const [deleting, setDeleting]       = useState(false)

  // Sync status from app
  useEffect(() => {
    if (app?.status) setStatus(app.status)
  }, [app?.status])

  // Auto-expand all rounds on load
  useEffect(() => {
    if (rounds.length > 0) setExpandedIds(new Set(rounds.map(r => r.id)))
  }, [ivData])

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['pursuits-apps'] })
    qc.invalidateQueries({ queryKey: ['pursuit-rounds', appId] })
    qc.invalidateQueries({ queryKey: ['growth-applications'] })
    qc.invalidateQueries({ queryKey: ['growth-interviews'] })
    qc.invalidateQueries({ queryKey: ['growth-timeline'] })
    qc.invalidateQueries({ queryKey: ['growth-summary'] })
    refetchRounds()
    onRefresh()
  }

  const handleStatusChange = async (s: ApplicationStatus) => {
    if (statusSaving) return
    setStatus(s)
    setStatusSaving(true)
    try { await updateApplicationStatus(appId, s) }
    finally { setStatusSaving(false); invalidate() }
  }

  const handleAnalyzeRound = async (roundId: number) => {
    setAnalyzingId(roundId)
    try { await analyzeInterview(roundId) }
    finally { setAnalyzingId(null); invalidate() }
  }

  const handleAnalyzeQ = (q: string, a: string) => {
    const msg = `请帮我分析这道面试题的回答，指出亮点和不足，并给出改进建议：\n\n题目：${q}\n\n我的回答：${a || '（未填写）'}`
    sendToCoach(msg)
  }

  const handleAnalyzeAll = async () => {
    const pending = rounds.filter(r => !r.ai_analysis && r.content_summary)
    if (pending.length === 0) return
    setAnalyzingAll(true)
    try {
      for (const r of pending) await analyzeInterview(r.id)
    } finally { setAnalyzingAll(false); invalidate() }
  }

  const handleDelete = async () => {
    if (!confirm(`删除「${app?.company}」的追踪及所有面试记录？`)) return
    setDeleting(true)
    try { await deleteApplication(appId); onClose(); onRefresh() }
    finally { setDeleting(false) }
  }

  const toggleExpand = (id: number) => {
    setExpandedIds(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const pendingAnalysis = rounds.filter(r => !r.ai_analysis && r.content_summary)

  if (!app) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <motion.div
        className="absolute inset-0"
        style={{ background: 'rgba(0,0,0,0.2)', backdropFilter: 'blur(8px)' }}
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        onClick={onClose}
      />

      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 12 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 12 }}
        transition={{ duration: 0.2, ease: [0.23, 1, 0.32, 1] }}
        className="relative w-full max-w-[540px] min-h-[660px] max-h-[88vh] flex flex-col rounded-[22px] overflow-hidden"
        style={{
          background: 'rgba(248,250,255,0.88)',
          backdropFilter: 'blur(40px)',
          WebkitBackdropFilter: 'blur(40px)',
          border: '1px solid rgba(255,255,255,0.7)',
          boxShadow: '0 32px 80px rgba(0,0,0,0.14), 0 4px 16px rgba(0,0,0,0.06)',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* ── Header ── */}
        <div className="px-6 pt-5 pb-4 shrink-0"
          style={{ borderBottom: '1px solid rgba(0,0,0,0.06)', background: 'linear-gradient(to bottom, rgba(37,99,235,0.02), transparent)' }}>
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <h2 className="text-[18px] font-extrabold text-[#1a1a1a] truncate">{app.company || '未知公司'}</h2>
              <p className="text-[12px] text-[#8E8E93] mt-0.5 truncate">{app.position || '未命名岗位'}</p>
            </div>
            <button onClick={onClose}
              className="w-7 h-7 rounded-full flex items-center justify-center cursor-pointer shrink-0"
              style={{ background: 'rgba(0,0,0,0.04)' }}
              onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0,0,0,0.08)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'rgba(0,0,0,0.04)')}>
              <X className="w-3.5 h-3.5" style={{ color: '#8E8E93' }} />
            </button>
          </div>

          <StatusSelector status={status} onSelect={handleStatusChange} disabled={statusSaving} />
        </div>

        {/* ── Body ── */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3"
          style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(0,0,0,0.08) transparent' }}>

          {/* Rounds header */}
          <div className="flex items-center justify-between">
            <p className="text-[12px] font-bold text-[#1a1a1a]">
              面试记录 <span className="font-normal text-[#8E8E93]">({rounds.length} 轮)</span>
            </p>
            {!addingRound && (
              <button onClick={() => setAddingRound(true)}
                className="flex items-center gap-1 text-[11px] font-semibold cursor-pointer"
                style={{ color: '#2563EB' }}>
                <Plus className="w-3.5 h-3.5" /> 添加轮次
              </button>
            )}
          </div>

          {/* Round list */}
          {rounds.length === 0 && !addingRound && (
            <div className="py-8 text-center">
              <p className="text-[11px] text-[#C7C7CC] mb-3">还没有面试记录</p>
              <button onClick={() => setAddingRound(true)}
                className="px-4 py-2 text-[11px] font-semibold text-white rounded-[9px] cursor-pointer"
                style={{ background: '#2563EB' }}>
                记录第一轮
              </button>
            </div>
          )}

          {rounds.map(r => (
            <RoundCard
              key={r.id}
              round={r}
              expanded={expandedIds.has(r.id)}
              onToggle={() => toggleExpand(r.id)}
              onAnalyzeRound={() => handleAnalyzeRound(r.id)}
              onAnalyzeQ={handleAnalyzeQ}
              analyzing={analyzingId === r.id}
            />
          ))}

          {/* Add round form */}
          <AnimatePresence>
            {addingRound && (
              <AddRoundForm
                applicationId={appId}
                company={app.company || ''}
                position={app.position || ''}
                onSuccess={() => { setAddingRound(false); invalidate() }}
                onCancel={() => setAddingRound(false)}
              />
            )}
          </AnimatePresence>

          {/* Analyze all button */}
          {pendingAnalysis.length > 0 && !addingRound && (
            <button onClick={handleAnalyzeAll} disabled={analyzingAll}
              className="w-full flex items-center justify-center gap-2 py-2.5 text-[11px] font-semibold rounded-[12px] cursor-pointer disabled:opacity-50 transition-all"
              style={{ background: 'rgba(8,145,178,0.08)', color: '#0891B2', border: '1px solid rgba(8,145,178,0.15)' }}>
              {analyzingAll
                ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> AI 分析中...</>
                : <><Sparkles className="w-3.5 h-3.5" /> 综合分析全部 ({pendingAnalysis.length} 轮待分析)</>
              }
            </button>
          )}

          {/* JD diagnosis CTA — always shown */}
          {!addingRound && (
            <button
              onClick={() => {
                const company = app.company || '目标公司'
                const position = app.position || '目标岗位'
                sendToCoach(
                  `帮我搜索「${company} ${position}」的真实招聘 JD，` +
                  `分析这个岗位的核心技能要求，结合我的技能画像找出我目前最关键的缺口，给出具体补强建议。`
                )
                onClose()
              }}
              className="w-full flex items-center justify-center gap-2 py-2.5 text-[11px] font-semibold rounded-[12px] cursor-pointer transition-all"
              style={{
                background: 'linear-gradient(135deg, rgba(37,99,235,0.08), rgba(124,58,237,0.08))',
                color: '#2563EB',
                border: '1px solid rgba(37,99,235,0.15)',
              }}
              onMouseEnter={e => (e.currentTarget.style.opacity = '0.8')}
              onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
            >
              <Sparkles className="w-3.5 h-3.5" style={{ color: '#7C3AED' }} />
              AI 帮我分析这个岗位的真实要求和缺口
            </button>
          )}
        </div>

        {/* ── Footer ── */}
        <div className="px-6 py-3.5 flex items-center justify-between shrink-0"
          style={{ borderTop: '1px solid rgba(0,0,0,0.06)', background: 'rgba(255,255,255,0.4)' }}>
          <button onClick={handleDelete} disabled={deleting}
            className="text-[10px] font-medium px-2.5 py-1.5 rounded-[7px] cursor-pointer transition-colors disabled:opacity-50"
            style={{ color: '#EF4444' }}
            onMouseEnter={e => (e.currentTarget.style.background = 'rgba(239,68,68,0.06)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
            {deleting ? '删除中...' : '删除追踪'}
          </button>
          <button onClick={onClose}
            className="text-[11px] font-semibold px-4 py-1.5 rounded-[9px] text-white cursor-pointer"
            style={{ background: '#2563EB' }}>
            完成
          </button>
        </div>
      </motion.div>
    </div>
  )
}
