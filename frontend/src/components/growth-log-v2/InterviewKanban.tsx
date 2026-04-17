import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { rawFetch } from '@/api/client'
import { Plus, X } from 'lucide-react'

const ease = [0.22, 1, 0.36, 1] as const

interface InterviewRecord {
  id: number
  company: string
  position: string
  round: string
  content_summary: string
  self_rating: string
  result: string
  stage: string
  reflection: string | null
  ai_analysis: Record<string, unknown> | null
  interview_at: string | null
  created_at: string
}

const STAGES = [
  { key: 'applied', label: '已投递', color: 'bg-slate-400' },
  { key: 'written_test', label: '笔试', color: 'bg-violet-400' },
  { key: 'interviewing', label: '面试中', color: 'bg-blue-400' },
  { key: 'offered', label: '已拿offer', color: 'bg-emerald-400' },
  { key: 'rejected', label: '未通过', color: 'bg-red-300' },
]

interface Props {
  interviews: InterviewRecord[]
  onRefresh: () => void
}

export function InterviewKanban({ interviews, onRefresh }: Props) {
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [showAdd, setShowAdd] = useState(false)

  // 只显示真实面试，过滤 AI 模拟
  const realInterviews = interviews.filter(i => i.company !== 'AI 模拟')

  const grouped = STAGES.map(stage => ({
    ...stage,
    items: realInterviews.filter(i => i.stage === stage.key),
  }))

  const selected = realInterviews.find(i => i.id === selectedId) || null

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-[13px] text-slate-400">
          共 {realInterviews.length} 条面试记录
        </p>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[13px] font-medium text-blue-600 hover:bg-blue-50 transition-all duration-200 cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5" />
          新增面试
        </button>
      </div>

      {/* Kanban columns */}
      {realInterviews.length === 0 ? (
        <div className="py-16 text-center">
          <p className="text-[14px] text-slate-400 mb-3">还没有面试记录</p>
          <button
            onClick={() => setShowAdd(true)}
            className="text-[13px] font-semibold text-blue-600 hover:text-blue-700 cursor-pointer"
          >
            记录你的第一场面试
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-5 gap-3">
          {grouped.map((stage) => (
            <div key={stage.key}>
              {/* Column header */}
              <div className="flex items-center gap-2 mb-3">
                <div className={`w-2 h-2 rounded-full ${stage.color}`} />
                <span className="text-[13px] font-semibold text-slate-700">
                  {stage.label}
                </span>
                <span className="text-[12px] text-slate-400 tabular-nums">
                  {stage.items.length}
                </span>
              </div>

              {/* Cards */}
              <div className="space-y-2 min-h-[100px]">
                {stage.items.length === 0 ? (
                  <div className="py-6 border border-dashed border-slate-200 rounded-lg text-center">
                    <span className="text-[12px] text-slate-300">暂无</span>
                  </div>
                ) : (
                  stage.items.map((item, i) => (
                    <motion.button
                      key={item.id}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.03, duration: 0.2, ease }}
                      onClick={() => setSelectedId(item.id)}
                      className="w-full text-left p-3 rounded-lg border border-slate-200/60 bg-white/70 hover:bg-white hover:border-slate-300/60 hover:-translate-y-px hover:shadow-sm transition-all duration-200 cursor-pointer"
                    >
                      <p className="text-[14px] font-semibold text-slate-700 truncate">
                        {item.company}
                      </p>
                      <p className="text-[13px] text-slate-500 truncate mt-0.5">
                        {item.position}
                      </p>
                      <div className="flex items-center justify-between mt-2">
                        <span className="text-[11px] text-slate-400">
                          {item.round}
                        </span>
                        <span className="text-[11px] text-slate-400">
                          {item.created_at?.slice(5, 10).replace('-', '/')}
                        </span>
                      </div>
                    </motion.button>
                  ))
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Detail panel (modal) */}
      <AnimatePresence>
        {selected && (
          <InterviewDetailModal
            interview={selected}
            onClose={() => setSelectedId(null)}
            onRefresh={onRefresh}
          />
        )}
      </AnimatePresence>

      {/* Add interview modal */}
      <AnimatePresence>
        {showAdd && (
          <AddInterviewModal
            onClose={() => setShowAdd(false)}
            onRefresh={onRefresh}
          />
        )}
      </AnimatePresence>
    </div>
  )
}


/* ── Detail Modal ── */

function InterviewDetailModal({
  interview,
  onClose,
  onRefresh,
}: {
  interview: InterviewRecord
  onClose: () => void
  onRefresh: () => void
}) {
  const qc = useQueryClient()
  const [contentSummary, setContentSummary] = useState(interview.content_summary || '')
  const [reflection, setReflection] = useState(interview.reflection || '')

  const updateMut = useMutation({
    mutationFn: (data: Record<string, string>) =>
      rawFetch(`/growth-log/interviews/${interview.id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      onRefresh()
      qc.invalidateQueries({ queryKey: ['growth-interviews'] })
    },
  })

  const deleteMut = useMutation({
    mutationFn: () =>
      rawFetch(`/growth-log/interviews/${interview.id}`, { method: 'DELETE' }),
    onSuccess: () => {
      onClose()
      onRefresh()
      qc.invalidateQueries({ queryKey: ['growth-interviews'] })
    },
  })

  const saveText = () => {
    const updates: Record<string, string> = {}
    if (contentSummary !== (interview.content_summary || '')) updates.content_summary = contentSummary
    if (reflection !== (interview.reflection || '')) updates.reflection = reflection
    if (Object.keys(updates).length > 0) updateMut.mutate(updates)
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 8 }}
        transition={{ duration: 0.2, ease }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-xl border border-slate-200 shadow-lg w-full max-w-[520px] mx-4 p-6 max-h-[85vh] overflow-y-auto"
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-5">
          <div>
            <h3 className="text-[18px] font-bold text-slate-800">{interview.company}</h3>
            <p className="text-[14px] text-slate-500 mt-0.5">{interview.position} · {interview.round}</p>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-slate-600 cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Editable: content summary */}
        <div className="mb-4">
          <p className="text-[12px] font-semibold text-slate-400 mb-1.5">面试内容（问了什么、答了什么）</p>
          <textarea
            value={contentSummary}
            onChange={(e) => setContentSummary(e.target.value)}
            onBlur={saveText}
            placeholder="记录面试中的问题和你的回答要点..."
            rows={3}
            className="w-full px-3 py-2 rounded-lg border border-slate-200 text-[13px] text-slate-700 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300 transition-all resize-none leading-relaxed"
          />
        </div>

        {/* Editable: reflection */}
        <div className="mb-5">
          <p className="text-[12px] font-semibold text-slate-400 mb-1.5">反思与收获</p>
          <textarea
            value={reflection}
            onChange={(e) => setReflection(e.target.value)}
            onBlur={saveText}
            placeholder="这次面试的感受、做得好的和不足的地方..."
            rows={2}
            className="w-full px-3 py-2 rounded-lg border border-slate-200 text-[13px] text-slate-700 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300 transition-all resize-none leading-relaxed"
          />
        </div>

        {/* Stage selector */}
        <div className="mb-4">
          <p className="text-[12px] font-semibold text-slate-400 mb-2">求职阶段</p>
          <div className="flex flex-wrap gap-2">
            {STAGES.map((s) => (
              <button
                key={s.key}
                onClick={() => updateMut.mutate({ stage: s.key })}
                className={`px-3 py-1.5 rounded-lg text-[12px] font-medium border transition-all duration-200 cursor-pointer ${
                  interview.stage === s.key
                    ? 'border-blue-400 bg-blue-50 text-blue-700'
                    : 'border-slate-200 text-slate-500 hover:border-blue-300 hover:bg-blue-50/50'
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {/* Self rating */}
        <div className="mb-5">
          <p className="text-[12px] font-semibold text-slate-400 mb-2">自评</p>
          <div className="flex gap-2">
            {[
              { key: 'good', label: '发挥好', color: 'border-emerald-400 bg-emerald-50 text-emerald-700' },
              { key: 'medium', label: '一般', color: 'border-amber-400 bg-amber-50 text-amber-700' },
              { key: 'bad', label: '发挥差', color: 'border-red-300 bg-red-50 text-red-600' },
            ].map((r) => (
              <button
                key={r.key}
                onClick={() => updateMut.mutate({ self_rating: r.key })}
                className={`px-3 py-1.5 rounded-lg text-[12px] font-medium border transition-all duration-200 cursor-pointer ${
                  interview.self_rating === r.key ? r.color : 'border-slate-200 text-slate-500 hover:border-slate-300'
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>

        {/* AI analysis preview (if available) */}
        {interview.ai_analysis && (interview.ai_analysis as Record<string, unknown>).source === 'mock_interview' && (
          <div className="mb-5 p-3 rounded-lg bg-blue-50/50 border border-blue-100/60">
            <p className="text-[12px] font-semibold text-blue-600 mb-1">AI 模拟面试评估</p>
            <p className="text-[13px] text-slate-600">
              得分 {String((interview.ai_analysis as Record<string, unknown>).overall_score ?? '')} · {String((interview.ai_analysis as Record<string, unknown>).summary ?? '')}
            </p>
          </div>
        )}

        {/* Date + delete */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-100">
          <span className="text-[12px] text-slate-400">
            {interview.created_at?.slice(0, 10)}
          </span>
          <button
            onClick={() => { if (confirm('确定删除这条面试记录？')) deleteMut.mutate() }}
            className="text-[12px] text-red-400 hover:text-red-600 transition-colors cursor-pointer"
          >
            删除记录
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}


/* ── Add Interview Modal ── */

function AddInterviewModal({
  onClose,
  onRefresh,
}: {
  onClose: () => void
  onRefresh: () => void
}) {
  const [company, setCompany] = useState('')
  const [position, setPosition] = useState('')
  const [round, setRound] = useState('技术一面')
  const [stage, setStage] = useState('applied')

  const qc = useQueryClient()

  const createMut = useMutation({
    mutationFn: (data: Record<string, string>) =>
      rawFetch('/growth-log/interviews', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      onClose()
      onRefresh()
      qc.invalidateQueries({ queryKey: ['growth-interviews'] })
    },
  })

  const handleSubmit = () => {
    if (!company.trim()) return
    createMut.mutate({
      company: company.trim(),
      position: position.trim(),
      round,
      stage,
      content_summary: '',
      self_rating: 'medium',
      result: 'pending',
    })
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 8 }}
        transition={{ duration: 0.2, ease }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-xl border border-slate-200 shadow-lg w-full max-w-[420px] mx-4 p-6"
      >
        <h3 className="text-[18px] font-bold text-slate-800 mb-5">新增面试记录</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-[12px] font-semibold text-slate-500 mb-1.5">公司名 *</label>
            <input
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="如 字节跳动"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 text-[14px] text-slate-800 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300 transition-all"
            />
          </div>
          <div>
            <label className="block text-[12px] font-semibold text-slate-500 mb-1.5">岗位</label>
            <input
              value={position}
              onChange={(e) => setPosition(e.target.value)}
              placeholder="如 后端工程师"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 text-[14px] text-slate-800 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300 transition-all"
            />
          </div>
          <div>
            <label className="block text-[12px] font-semibold text-slate-500 mb-1.5">面试轮次</label>
            <input
              value={round}
              onChange={(e) => setRound(e.target.value)}
              placeholder="如 技术一面、HR面"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 text-[14px] text-slate-800 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300 transition-all"
            />
          </div>
          <div>
            <label className="block text-[12px] font-semibold text-slate-500 mb-2">当前阶段</label>
            <div className="flex flex-wrap gap-2">
              {STAGES.map((s) => (
                <button
                  key={s.key}
                  onClick={() => setStage(s.key)}
                  className={`px-3 py-1.5 rounded-lg text-[12px] font-medium border transition-all duration-200 cursor-pointer ${
                    stage === s.key
                      ? 'border-blue-400 bg-blue-50 text-blue-700'
                      : 'border-slate-200 text-slate-500 hover:border-blue-300'
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-[13px] font-medium text-slate-500 hover:bg-slate-50 transition-all cursor-pointer"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={!company.trim() || createMut.isPending}
            className="px-5 py-2 rounded-lg bg-blue-600 text-white text-[13px] font-bold hover:bg-blue-700 active:scale-[0.98] transition-all disabled:opacity-30 cursor-pointer"
          >
            {createMut.isPending ? '保存中...' : '保存'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}
