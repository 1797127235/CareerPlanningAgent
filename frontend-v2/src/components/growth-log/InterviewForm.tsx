import { useState } from 'react'
import { X, Building2, Briefcase, RefreshCw, MessagesSquare, Star, Flag, FileText, Plus } from 'lucide-react'
import type { InterviewData, GrowthEntry } from './mockData'

interface InterviewFormProps {
  onClose: () => void
  onSaved?: () => void
  onAddEntry: (data: Partial<GrowthEntry>) => Promise<unknown> | unknown
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

  const inputCls =
    'w-full px-4 py-3 text-[14px] rounded-2xl outline-none transition-all bg-[var(--bg-paper)] border placeholder:text-[var(--ink-3)] focus:border-[var(--chestnut)] focus:ring-2 focus:ring-[var(--chestnut)]/10'
  const qaCls =
    'w-full px-3.5 py-2.5 text-[13px] rounded-xl outline-none transition-all bg-[var(--bg-paper)] border placeholder:text-[var(--ink-3)] focus:border-[var(--chestnut)] focus:ring-2 focus:ring-[var(--chestnut)]/10'

  const Label = ({ icon: Icon, children }: { icon: any; children: React.ReactNode }) => (
    <label className="flex items-center gap-2 text-[13px] font-semibold mb-2" style={{ color: 'var(--ink-1)' }}>
      <Icon className="w-4 h-4" style={{ color: 'var(--ink-3)' }} />
      {children}
    </label>
  )

  return (
    <div className="space-y-5 max-h-[70vh] overflow-y-auto pr-1">
      <div className="space-y-1">
        <h3 className="text-[20px] font-bold" style={{ fontFamily: 'var(--font-serif)', color: 'var(--ink-1)' }}>
          {isEdit ? '编辑面试复盘' : '新增面试记录'}
        </h3>
        <p className="text-[13px]" style={{ color: 'var(--ink-3)' }}>
          记录每一次面试，沉淀成长与收获
        </p>
      </div>

      <div>
        <Label icon={Building2}>公司名称 *</Label>
        <input
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          placeholder="例如：字节跳动"
          className={inputCls}
          style={{ color: 'var(--ink-1)', borderColor: 'var(--line)' }}
        />
      </div>

      <div>
        <Label icon={Briefcase}>岗位</Label>
        <input
          value={position}
          onChange={(e) => setPosition(e.target.value)}
          placeholder="例如：后端开发实习"
          className={inputCls}
          style={{ color: 'var(--ink-1)', borderColor: 'var(--line)' }}
        />
      </div>

      <div>
        <Label icon={RefreshCw}>轮次</Label>
        <select
          value={round}
          onChange={(e) => setRound(e.target.value)}
          className={inputCls}
          style={{ color: 'var(--ink-1)', borderColor: 'var(--line)' }}
        >
          {ROUND_OPTIONS.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </div>

      <div>
        <Label icon={MessagesSquare}>问了什么 · 我怎么答的</Label>
        <div className="space-y-3">
          {questions.map((qa, idx) => (
            <div
              key={idx}
              className="p-3.5 rounded-2xl relative"
              style={{ background: 'var(--bg-paper)', border: '1px solid var(--line)' }}
            >
              <button
                onClick={() => removeQuestion(idx)}
                className="absolute right-3 top-3 transition-colors cursor-pointer"
                style={{ color: 'var(--ink-3)' }}
                aria-label="删除"
              >
                <X className="w-3.5 h-3.5" />
              </button>
              <input
                value={qa.q}
                onChange={(e) => updateQuestion(idx, 'q', e.target.value)}
                className={qaCls + ' mb-2 pr-8'}
                style={{ color: 'var(--ink-1)', borderColor: 'var(--line)' }}
                placeholder="Q: 面试问题"
              />
              <input
                value={qa.a}
                onChange={(e) => updateQuestion(idx, 'a', e.target.value)}
                className={qaCls}
                style={{ color: 'var(--ink-1)', borderColor: 'var(--line)' }}
                placeholder="A: 我的回答"
              />
            </div>
          ))}
        </div>
        <button
          onClick={addQuestion}
          className="mt-3 flex items-center gap-1 text-[13px] font-medium cursor-pointer transition-colors"
          style={{ color: 'var(--chestnut)' }}
        >
          <Plus className="w-3.5 h-3.5" /> 加一题
        </button>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div>
          <Label icon={Star}>自评</Label>
          <div className="flex items-center gap-4">
            {[
              { key: 'good' as const, label: '好' },
              { key: 'medium' as const, label: '一般' },
              { key: 'bad' as const, label: '差' },
            ].map((o) => (
              <label
                key={o.key}
                className="flex items-center gap-1.5 text-[13px] cursor-pointer"
                style={{ color: 'var(--ink-1)' }}
              >
                <input
                  type="radio"
                  name="self_rating"
                  checked={selfRating === o.key}
                  onChange={() => setSelfRating(o.key)}
                  className="cursor-pointer"
                />
                {o.label}
              </label>
            ))}
          </div>
        </div>
        <div>
          <Label icon={Flag}>结果</Label>
          <div className="flex items-center gap-4">
            {[
              { key: 'passed' as const, label: '通过' },
              { key: 'failed' as const, label: '未通过' },
              { key: 'pending' as const, label: '待定' },
            ].map((o) => (
              <label
                key={o.key}
                className="flex items-center gap-1.5 text-[13px] cursor-pointer"
                style={{ color: 'var(--ink-1)' }}
              >
                <input
                  type="radio"
                  name="result"
                  checked={result === o.key}
                  onChange={() => setResult(o.key)}
                  className="cursor-pointer"
                />
                {o.label}
              </label>
            ))}
          </div>
        </div>
      </div>

      <div>
        <Label icon={FileText}>复盘感受</Label>
        <textarea
          value={reflection}
          onChange={(e) => setReflection(e.target.value)}
          rows={3}
          className={inputCls + ' resize-none'}
          style={{ color: 'var(--ink-1)', borderColor: 'var(--line)' }}
          placeholder="总结一下这次面试的得失..."
        />
      </div>

      {err && (
        <div
          className="px-3 py-2 text-[12px] rounded-lg border"
          style={{ color: '#B85C38', background: 'rgba(184,92,56,0.06)', borderColor: 'rgba(184,92,56,0.15)' }}
        >
          {err}
        </div>
      )}
      <div className="flex items-center justify-end gap-3 pt-2">
        <button
          onClick={onClose}
          disabled={saving}
          className="px-5 py-2.5 rounded-2xl text-[14px] font-medium transition-all cursor-pointer disabled:opacity-40"
          style={{ color: 'var(--ink-2)' }}
        >
          取消
        </button>
        <button
          onClick={handleSave}
          disabled={saving || !company.trim()}
          className="px-6 py-2.5 rounded-2xl text-[14px] font-semibold text-white transition-all cursor-pointer disabled:opacity-40"
          style={{ background: 'var(--chestnut)' }}
        >
          {saving ? '保存中…' : '保存'}
        </button>
      </div>
    </div>
  )
}
