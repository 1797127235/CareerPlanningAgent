import { useState } from 'react'
import {
  X, Building2, Briefcase, RefreshCw, MessagesSquare,
  Star, Flag, FileText, Plus,
} from 'lucide-react'
import type { InterviewData, GrowthEntry } from './mockData'

interface InterviewFormProps {
  onClose: () => void
  onSaved?: () => void
  onAddEntry: (data: Partial<GrowthEntry>) => Promise<unknown> | unknown
  onCreateInterview?: (data: {
    company: string
    position?: string
    round?: string
    content_summary: string
    self_rating?: string
    result?: string
    reflection?: string
  }) => Promise<unknown> | unknown
  initialEntry?: GrowthEntry | null
  onUpdate?: (id: number, data: Partial<GrowthEntry>) => Promise<unknown>
}

const ROUND_OPTIONS = ['技术一面', '技术二面', '技术三面', 'HR 面', '综合面', '其他']

export function InterviewForm({
  onClose,
  onSaved,
  onAddEntry,
  onCreateInterview,
  initialEntry,
  onUpdate,
}: InterviewFormProps) {
  const initData = (initialEntry?.structured_data as InterviewData | null) || null
  const isEdit = !!initialEntry
  const [company, setCompany] = useState(initData?.company ?? '')
  const [position, setPosition] = useState(initData?.position ?? '')
  const [round, setRound] = useState(initData?.round ?? '技术一面')
  const [questions, setQuestions] = useState<{ q: string; a: string }[]>(
    initData?.questions?.length ? initData.questions : [{ q: '', a: '' }]
  )
  const [selfRating, setSelfRating] = useState<'good' | 'medium' | 'bad'>(
    initData?.self_rating ?? 'medium'
  )
  const [result, setResult] = useState<'passed' | 'failed' | 'pending'>(
    initData?.result ?? 'pending'
  )
  const [reflection, setReflection] = useState(initData?.reflection ?? '')
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const addQuestion = () => setQuestions([...questions, { q: '', a: '' }])
  const removeQuestion = (idx: number) => setQuestions(questions.filter((_, i) => i !== idx))
  const updateQuestion = (idx: number, field: 'q' | 'a', value: string) => {
    const next = [...questions]
    next[idx][field] = value
    setQuestions(next)
  }

  const handleSave = async () => {
    if (saving) return
    if (!company.trim()) {
      setErr('请填公司名称')
      return
    }
    const structured: InterviewData = {
      company: company.trim(),
      position: position.trim() || '未知岗位',
      round,
      questions: questions.filter((qa) => qa.q.trim()),
      self_rating: selfRating,
      result,
      reflection,
    }
    setSaving(true)
    setErr(null)
    try {
      if (isEdit && onUpdate && initialEntry) {
        await onUpdate(initialEntry.id, {
          content: `${structured.company} ${structured.round}`,
          tags: ['面试', structured.company],
          structured_data: structured as any,
        })
      } else if (onCreateInterview) {
        const contentSummary = structured.questions
          .map((qa) => `Q: ${qa.q}\nA: ${qa.a}`)
          .join('\n\n')
        await onCreateInterview({
          company: structured.company,
          position: structured.position,
          round: structured.round,
          content_summary: contentSummary,
          self_rating: structured.self_rating,
          result: structured.result,
          reflection: structured.reflection,
        })
      } else {
        await onAddEntry({
          content: `${structured.company} ${structured.round}`,
          category: 'interview',
          tags: ['面试', structured.company],
          structured_data: structured as any,
          is_plan: false,
          status: 'done',
          due_type: null,
          due_at: null,
          completed_at: null,
          ai_suggestions: null,
        })
      }
      onSaved?.()
      onClose()
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  const inputStyle: React.CSSProperties = {
    background: '#EDE8DE',
    border: '1px solid rgba(107,62,46,0.08)',
    color: '#3A3028',
    borderRadius: 16,
    boxShadow: 'inset 0 1px 3px rgba(60,50,40,0.06)',
  }

  const sectionStyle: React.CSSProperties = {
    background: '#EDE8DE',
    border: '1px solid rgba(107,62,46,0.08)',
    borderRadius: 18,
    boxShadow: 'inset 0 1px 3px rgba(60,50,40,0.06)',
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-1.5">
        <h2
          className="text-[22px] font-bold tracking-tight"
          style={{ fontFamily: 'var(--font-serif)', color: '#2A2118' }}
        >
          {isEdit ? '编辑面试复盘' : '新增面试记录'}
        </h2>
        <p className="text-[13px]" style={{ color: '#9A8B7A' }}>
          记录每一次面试，沉淀成长与收获
        </p>
      </div>

      {/* 公司名称 */}
      <div className="space-y-2.5">
        <label className="flex items-center gap-2 text-[13px]" style={{ color: '#5A4D3F' }}>
          <Building2 className="w-4 h-4" style={{ color: '#9A8B7A' }} />
          <span className="font-medium">公司名称</span>
          <span style={{ color: '#B85C38' }}>*</span>
        </label>
        <input
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          placeholder="例如：字节跳动"
          className="w-full px-5 py-3.5 text-[14px] outline-none transition-all placeholder:text-[#C4B8A8] focus:border-[#B85C38]/40"
          style={inputStyle}
        />
      </div>

      {/* 岗位 */}
      <div className="space-y-2.5">
        <label className="flex items-center gap-2 text-[13px]" style={{ color: '#5A4D3F' }}>
          <Briefcase className="w-4 h-4" style={{ color: '#9A8B7A' }} />
          <span className="font-medium">岗位</span>
        </label>
        <input
          value={position}
          onChange={(e) => setPosition(e.target.value)}
          placeholder="例如：后端开发实习"
          className="w-full px-5 py-3.5 text-[14px] outline-none transition-all placeholder:text-[#C4B8A8] focus:border-[#B85C38]/40"
          style={inputStyle}
        />
      </div>

      {/* 轮次 */}
      <div className="space-y-2.5">
        <label className="flex items-center gap-2 text-[13px]" style={{ color: '#5A4D3F' }}>
          <RefreshCw className="w-4 h-4" style={{ color: '#9A8B7A' }} />
          <span className="font-medium">轮次</span>
        </label>
        <select
          value={round}
          onChange={(e) => setRound(e.target.value)}
          className="w-full px-5 py-3.5 text-[14px] outline-none transition-all appearance-none cursor-pointer focus:border-[#B85C38]/40"
          style={inputStyle}
        >
          {ROUND_OPTIONS.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
      </div>

      {/* Q&A */}
      <div className="space-y-3">
        <label className="flex items-center gap-2 text-[13px]" style={{ color: '#5A4D3F' }}>
          <MessagesSquare className="w-4 h-4" style={{ color: '#9A8B7A' }} />
          <span className="font-medium">问了什么 · 我怎么答的</span>
        </label>
        <div className="space-y-3">
          {questions.map((qa, idx) => (
            <div
              key={idx}
              className="p-4 relative"
              style={sectionStyle}
            >
              <button
                onClick={() => removeQuestion(idx)}
                className="absolute right-3 top-3 transition-colors cursor-pointer"
                style={{ color: '#C4B8A8' }}
                aria-label="删除"
              >
                <X className="w-3.5 h-3.5" />
              </button>
              <input
                value={qa.q}
                onChange={(e) => updateQuestion(idx, 'q', e.target.value)}
                placeholder="面试问题"
                className="w-full pr-8 px-4 py-2.5 text-[13px] outline-none transition-all placeholder:text-[#C4B8A8] focus:border-[#B85C38]/40 mb-2"
                style={inputStyle}
              />
              <input
                value={qa.a}
                onChange={(e) => updateQuestion(idx, 'a', e.target.value)}
                placeholder="我的回答"
                className="w-full px-4 py-2.5 text-[13px] outline-none transition-all placeholder:text-[#C4B8A8] focus:border-[#B85C38]/40"
                style={inputStyle}
              />
            </div>
          ))}
        </div>
        <button
          onClick={addQuestion}
          className="flex items-center gap-1.5 text-[13px] font-medium cursor-pointer transition-colors px-3 py-1.5 rounded-xl"
          style={{ color: '#6B3E2E', background: 'rgba(107,62,46,0.06)' }}
        >
          <Plus className="w-3.5 h-3.5" /> 加一题
        </button>
      </div>

      {/* 自评 + 结果 */}
      <div className="grid grid-cols-2 gap-8">
        <div className="space-y-3">
          <label className="flex items-center gap-2 text-[13px]" style={{ color: '#5A4D3F' }}>
            <Star className="w-4 h-4" style={{ color: '#9A8B7A' }} />
            <span className="font-medium">自评</span>
          </label>
          <div className="flex items-center gap-5">
            {[
              { key: 'good' as const, label: '好' },
              { key: 'medium' as const, label: '一般' },
              { key: 'bad' as const, label: '差' },
            ].map((o) => (
              <label
                key={o.key}
                className="flex items-center gap-2 text-[14px] cursor-pointer"
                style={{ color: '#3A3028' }}
              >
                <input
                  type="radio"
                  name="self_rating"
                  checked={selfRating === o.key}
                  onChange={() => setSelfRating(o.key)}
                  className="cursor-pointer accent-[#B85C38]"
                />
                {o.label}
              </label>
            ))}
          </div>
        </div>
        <div className="space-y-3">
          <label className="flex items-center gap-2 text-[13px]" style={{ color: '#5A4D3F' }}>
            <Flag className="w-4 h-4" style={{ color: '#9A8B7A' }} />
            <span className="font-medium">结果</span>
          </label>
          <div className="flex items-center gap-5">
            {[
              { key: 'passed' as const, label: '通过' },
              { key: 'failed' as const, label: '未通过' },
              { key: 'pending' as const, label: '待定' },
            ].map((o) => (
              <label
                key={o.key}
                className="flex items-center gap-2 text-[14px] cursor-pointer"
                style={{ color: '#3A3028' }}
              >
                <input
                  type="radio"
                  name="result"
                  checked={result === o.key}
                  onChange={() => setResult(o.key)}
                  className="cursor-pointer accent-[#B85C38]"
                />
                {o.label}
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* 复盘感受 */}
      <div className="space-y-2.5">
        <label className="flex items-center gap-2 text-[13px]" style={{ color: '#5A4D3F' }}>
          <FileText className="w-4 h-4" style={{ color: '#9A8B7A' }} />
          <span className="font-medium">复盘感受</span>
        </label>
        <textarea
          value={reflection}
          onChange={(e) => setReflection(e.target.value)}
          rows={3}
          className="w-full px-5 py-3.5 text-[14px] outline-none transition-all resize-none placeholder:text-[#C4B8A8] focus:border-[#B85C38]/40"
          style={inputStyle}
          placeholder="总结一下这次面试的得失..."
        />
      </div>

      {err && (
        <div
          className="px-4 py-2.5 text-[13px] rounded-xl"
          style={{
            color: '#B85C38',
            background: 'rgba(184,92,56,0.06)',
            border: '1px solid rgba(184,92,56,0.12)',
          }}
        >
          {err}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-end gap-3 pt-2">
        <button
          onClick={onClose}
          disabled={saving}
          className="px-6 py-2.5 rounded-2xl text-[14px] font-medium transition-all cursor-pointer disabled:opacity-40"
          style={{ color: '#9A8B7A' }}
        >
          取消
        </button>
        <button
          onClick={handleSave}
          disabled={saving || !company.trim()}
          className="px-7 py-2.5 rounded-2xl text-[14px] font-semibold text-white transition-all cursor-pointer disabled:opacity-40"
          style={{ background: '#B85C38', boxShadow: '0 2px 8px rgba(184,92,56,0.25)' }}
        >
          {saving ? '保存中…' : '保存'}
        </button>
      </div>
    </div>
  )
}
