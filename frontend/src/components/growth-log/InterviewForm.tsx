/**
 * 面试轮次 Q&A 表单 — 在岗位追踪 modal 内使用
 * 用户选轮次，逐条添加面试题+自己的回答
 */
import { useState } from 'react'
import { Plus, X, Check } from 'lucide-react'
import { createInterview } from '@/api/growthLog'
import type { InterviewRecord } from '@/api/growthLog'

const ROUNDS = ['技术一面', '技术二面', '技术三面', 'HR面', '终面', '笔试']

interface QA { question: string; answer: string }

interface Props {
  applicationId: number
  company: string
  position: string
  onSuccess: (record: InterviewRecord) => void
  onCancel: () => void
}

export function InterviewRoundForm({ applicationId, company, position, onSuccess, onCancel }: Props) {
  const [round, setRound] = useState('技术一面')
  const [qaList, setQaList] = useState<QA[]>([{ question: '', answer: '' }])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  function updateQA(i: number, field: 'question' | 'answer', value: string) {
    setQaList(qaList.map((qa, idx) => idx === i ? { ...qa, [field]: value } : qa))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const valid = qaList.filter(qa => qa.question.trim())
    if (valid.length === 0) { setError('至少记录一道面试题'); return }
    setSaving(true)
    setError('')
    try {
      const content = valid
        .map((qa, i) => `Q${i + 1}: ${qa.question}\nA${i + 1}: ${qa.answer || '(未填写)'}`)
        .join('\n\n')
      const record = await createInterview({
        company, position, round,
        content_summary: content,
        self_rating: 'medium',
        result: 'pending',
        application_id: applicationId,
      })
      onSuccess(record)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 pt-3 border-t border-[#F2F2F7]">
      {/* Round select */}
      <div className="flex gap-1.5 flex-wrap">
        {ROUNDS.map(r => (
          <button type="button" key={r} onClick={() => setRound(r)}
            className={`px-2.5 py-1 text-[11px] font-medium rounded-md border transition-all cursor-pointer ${
              round === r ? 'bg-blue-50 border-blue-300 text-blue-700' : 'border-slate-200 text-slate-400 hover:border-slate-300'
            }`}
          >{r}</button>
        ))}
      </div>

      {/* Q&A pairs */}
      <div className="space-y-2">
        {qaList.map((qa, i) => (
          <div key={i} className="relative p-2.5 rounded-lg bg-[#FAFAFA] border border-[#F2F2F7]">
            {qaList.length > 1 && (
              <button type="button" onClick={() => setQaList(qaList.filter((_, idx) => idx !== i))}
                className="absolute top-1.5 right-1.5 p-0.5 text-slate-300 hover:text-red-400 cursor-pointer">
                <X className="w-3 h-3" />
              </button>
            )}
            <input value={qa.question} onChange={e => updateQA(i, 'question', e.target.value)}
              placeholder={`面试题 ${i + 1}`}
              className="w-full text-[12px] font-medium text-[#1a1a1a] bg-transparent border-0 outline-none placeholder:text-slate-300 mb-1" />
            <textarea value={qa.answer} onChange={e => updateQA(i, 'answer', e.target.value)}
              placeholder="我的回答（选填）"
              rows={1}
              className="w-full text-[11px] text-[#636366] bg-transparent border-0 outline-none placeholder:text-slate-300 resize-none" />
          </div>
        ))}
      </div>
      <button type="button" onClick={() => setQaList([...qaList, { question: '', answer: '' }])}
        className="flex items-center gap-1 text-[11px] font-medium text-[var(--blue)] hover:text-blue-700 cursor-pointer">
        <Plus className="w-3 h-3" /> 再加一题
      </button>

      {error && <p className="text-[11px] text-red-500">{error}</p>}

      <div className="flex gap-2">
        <button type="submit" disabled={saving}
          className="flex items-center gap-1 px-3 py-1.5 bg-[var(--blue)] text-white text-[11px] font-medium rounded-md hover:opacity-90 disabled:opacity-50 cursor-pointer">
          {saving ? <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <Check className="w-3 h-3" />}
          {saving ? '保存中' : '保存'}
        </button>
        <button type="button" onClick={onCancel}
          className="px-3 py-1.5 text-[11px] text-slate-500 border border-slate-200 rounded-md hover:bg-slate-50 cursor-pointer">
          取消
        </button>
      </div>
    </form>
  )
}
