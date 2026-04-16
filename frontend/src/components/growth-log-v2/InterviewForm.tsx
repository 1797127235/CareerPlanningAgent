import { useState } from 'react'
import { X } from 'lucide-react'
import type { InterviewData, GrowthEntry } from './mockData'

interface InterviewFormProps {
  onClose: () => void
  onSaved?: () => void
  onAddEntry: (data: Partial<GrowthEntry>) => Promise<unknown> | unknown
  /** 编辑模式：传入现有 entry，保存时调 onUpdate 而不是 onAddEntry */
  initialEntry?: GrowthEntry | null
  onUpdate?: (id: number, data: Partial<GrowthEntry>) => Promise<unknown>
}

const ROUND_OPTIONS = ['技术一面', '技术二面', '技术三面', 'HR 面', '综合面', '其他']

export function InterviewForm({
  onClose,
  onSaved,
  onAddEntry,
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

  return (
    <div className="bg-white rounded-xl shadow-xl p-5 max-h-[80vh] overflow-y-auto">
      <h3 className="text-[16px] font-bold text-slate-900 mb-4">
        {isEdit ? '编辑面试复盘' : '面试复盘'}
      </h3>
      <div className="space-y-4">
        <div>
          <label className="block text-[12px] font-semibold text-slate-500 mb-1">公司名称</label>
          <input
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            className="w-full px-3 py-2 text-[13px] border border-slate-300 rounded-lg outline-none focus:border-blue-500"
            placeholder="例如：字节跳动"
          />
        </div>
        <div>
          <label className="block text-[12px] font-semibold text-slate-500 mb-1">岗位</label>
          <input
            value={position}
            onChange={(e) => setPosition(e.target.value)}
            className="w-full px-3 py-2 text-[13px] border border-slate-300 rounded-lg outline-none focus:border-blue-500"
            placeholder="例如：后端开发实习"
          />
        </div>
        <div>
          <label className="block text-[12px] font-semibold text-slate-500 mb-1">轮次</label>
          <select
            value={round}
            onChange={(e) => setRound(e.target.value)}
            className="w-full px-3 py-2 text-[13px] border border-slate-300 rounded-lg outline-none focus:border-blue-500 bg-white"
          >
            {ROUND_OPTIONS.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-[12px] font-semibold text-slate-500 mb-2">问了什么 · 我怎么答的</label>
          <div className="space-y-3">
            {questions.map((qa, idx) => (
              <div key={idx} className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 relative">
                <button
                  onClick={() => removeQuestion(idx)}
                  className="absolute right-2 top-2 text-slate-300 hover:text-red-500 cursor-pointer"
                  aria-label="删除"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
                <input
                  value={qa.q}
                  onChange={(e) => updateQuestion(idx, 'q', e.target.value)}
                  className="w-full pr-6 px-2 py-1.5 text-[13px] border border-slate-300 rounded-md outline-none focus:border-blue-500 mb-2 bg-white"
                  placeholder="Q: 面试问题"
                />
                <input
                  value={qa.a}
                  onChange={(e) => updateQuestion(idx, 'a', e.target.value)}
                  className="w-full px-2 py-1.5 text-[13px] border border-slate-300 rounded-md outline-none focus:border-blue-500 bg-white"
                  placeholder="A: 我的回答"
                />
              </div>
            ))}
          </div>
          <button
            onClick={addQuestion}
            className="mt-2 text-[12px] font-medium text-blue-600 hover:text-blue-800 cursor-pointer"
          >
            + 加一题
          </button>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-[12px] font-semibold text-slate-500 mb-1">自评</label>
            <div className="flex items-center gap-3">
              {[
                { key: 'good', label: '好' },
                { key: 'medium', label: '一般' },
                { key: 'bad', label: '差' },
              ].map((o) => (
                <label key={o.key} className="flex items-center gap-1 text-[13px] text-slate-700 cursor-pointer">
                  <input
                    type="radio"
                    name="self_rating"
                    checked={selfRating === o.key}
                    onChange={() => setSelfRating(o.key as any)}
                    className="cursor-pointer"
                  />
                  {o.label}
                </label>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-[12px] font-semibold text-slate-500 mb-1">结果</label>
            <div className="flex items-center gap-3">
              {[
                { key: 'passed', label: '通过' },
                { key: 'failed', label: '未通过' },
                { key: 'pending', label: '待定' },
              ].map((o) => (
                <label key={o.key} className="flex items-center gap-1 text-[13px] text-slate-700 cursor-pointer">
                  <input
                    type="radio"
                    name="result"
                    checked={result === o.key}
                    onChange={() => setResult(o.key as any)}
                    className="cursor-pointer"
                  />
                  {o.label}
                </label>
              ))}
            </div>
          </div>
        </div>

        <div>
          <label className="block text-[12px] font-semibold text-slate-500 mb-1">复盘感受</label>
          <textarea
            value={reflection}
            onChange={(e) => setReflection(e.target.value)}
            rows={2}
            className="w-full px-3 py-2 text-[13px] border border-slate-300 rounded-lg outline-none focus:border-blue-500 resize-none"
            placeholder="总结一下这次面试的得失..."
          />
        </div>
      </div>

      {err && (
        <div className="mt-4 px-3 py-2 text-[12px] text-red-700 bg-red-50 border border-red-200 rounded-md">
          {err}
        </div>
      )}
      <div className="mt-6 flex items-center justify-end gap-3">
        <button
          onClick={onClose}
          disabled={saving}
          className="px-4 py-2 text-[13px] font-medium text-slate-500 hover:text-slate-800 disabled:opacity-40 cursor-pointer"
        >
          取消
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 text-[13px] font-semibold text-white bg-slate-900 hover:bg-blue-700 disabled:opacity-40 rounded-lg transition-colors cursor-pointer"
        >
          {saving ? '保存中…' : '保存'}
        </button>
      </div>
    </div>
  )
}
