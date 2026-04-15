import { useState } from 'react'
import { generateSjt, submitSjt, type SjtQuestion, type SjtAnswer } from '@/api/profiles'

export function SjtQuiz({ onComplete, onCancel }: { onComplete: () => void; onCancel: () => void }) {
  const [questions, setQuestions] = useState<SjtQuestion[]>([])
  const [sessionId, setSessionId] = useState('')
  const [answers, setAnswers] = useState<SjtAnswer[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [started, setStarted] = useState(false)

  const start = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await generateSjt()
      setQuestions(res.questions)
      setSessionId(res.session_id)
      setStarted(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : '生成失败')
    } finally {
      setLoading(false)
    }
  }

  const setBest = (qid: string, oid: string) => {
    setAnswers((prev) => {
      const existing = prev.find((a) => a.question_id === qid)
      if (existing) {
        return prev.map((a) => (a.question_id === qid ? { ...a, best: oid } : a))
      }
      return [...prev, { question_id: qid, best: oid, worst: '' }]
    })
  }

  const setWorst = (qid: string, oid: string) => {
    setAnswers((prev) => {
      const existing = prev.find((a) => a.question_id === qid)
      if (existing) {
        return prev.map((a) => (a.question_id === qid ? { ...a, worst: oid } : a))
      }
      return [...prev, { question_id: qid, best: '', worst: oid }]
    })
  }

  const handleSubmit = async () => {
    if (answers.length < questions.length) {
      setError('还有题目没做完')
      return
    }
    setLoading(true)
    try {
      await submitSjt(sessionId, answers)
      onComplete()
    } catch (e) {
      setError(e instanceof Error ? e.message : '提交失败')
    } finally {
      setLoading(false)
    }
  }

  if (!started) {
    return (
      <div className="rounded-xl border border-[var(--line)] bg-[var(--bg-card)] p-6 md:p-8 text-center">
        <p className="font-display text-[var(--fs-display-sm)] text-[var(--ink-1)] mb-2">准备开始 3 分钟小测</p>
        <p className="text-[var(--fs-body)] text-[var(--ink-2)] mb-6">没有标准答案，选最真实的就好。</p>
        {error && <p className="mb-4 text-[13px] text-red-600">{error}</p>}
        <div className="flex items-center justify-center gap-3">
          <button onClick={start} disabled={loading} className="px-5 py-2.5 rounded-full bg-[var(--chestnut)] text-white text-[13px] font-medium hover:opacity-90 disabled:opacity-50">
            {loading ? '生成中…' : '开始'}
          </button>
          <button onClick={onCancel} className="px-5 py-2.5 rounded-full text-[13px] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)]">
            取消
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-[var(--line)] bg-[var(--bg-card)] p-5 md:p-6 space-y-6">
      {questions.map((q, idx) => {
        const ans = answers.find((a) => a.question_id === q.id)
        return (
          <div key={q.id} className="pb-6 border-b border-[var(--line)] last:border-0 last:pb-0">
            <p className="text-[13px] font-medium text-[var(--ink-3)] mb-2">问题 {idx + 1} / {questions.length}</p>
            <p className="text-[var(--fs-body-lg)] text-[var(--ink-1)] mb-4 leading-[var(--lh-body-zh)]">{q.scenario}</p>
            <div className="space-y-2">
              {q.options.map((o) => (
                <div key={o.id} className="flex items-center gap-3">
                  <input
                    type="radio"
                    name={`best-${q.id}`}
                    checked={ans?.best === o.id}
                    onChange={() => setBest(q.id, o.id)}
                    className="accent-[var(--chestnut)]"
                  />
                  <span className="text-[12px] text-[var(--ink-3)] shrink-0">最像我会做的</span>
                  <input
                    type="radio"
                    name={`worst-${q.id}`}
                    checked={ans?.worst === o.id}
                    onChange={() => setWorst(q.id, o.id)}
                    className="accent-[var(--ink-3)]"
                  />
                  <span className="text-[12px] text-[var(--ink-3)] shrink-0">最不像</span>
                  <span className="text-[var(--fs-body)] text-[var(--ink-2)]">{o.text}</span>
                </div>
              ))}
            </div>
          </div>
        )
      })}
      {error && <p className="text-[13px] text-red-600">{error}</p>}
      <div className="flex items-center gap-3">
        <button onClick={handleSubmit} disabled={loading} className="px-5 py-2.5 rounded-full bg-[var(--chestnut)] text-white text-[13px] font-medium hover:opacity-90 disabled:opacity-50">
          {loading ? '提交中…' : '提交'}
        </button>
        <button onClick={onCancel} className="px-5 py-2.5 rounded-full text-[13px] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)]">
          取消
        </button>
      </div>
    </div>
  )
}
