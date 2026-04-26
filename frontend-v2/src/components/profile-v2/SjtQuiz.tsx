import { useState, useCallback, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { generateSjt, submitSjt, saveSjtProgress, getSjtProgress, type SjtQuestion, type SjtAnswer } from '@/api/profiles'

/* ── Design Tokens ── */
const serif = { fontFamily: 'var(--font-serif), Georgia, "Noto Serif SC", serif' }
const sans = { fontFamily: 'var(--font-sans), "Noto Sans SC", system-ui, sans-serif' }
const ink = (n: 1 | 2 | 3) =>
  n === 1 ? 'var(--ink-1)' : n === 2 ? 'var(--ink-2)' : 'var(--ink-3)'

const BEST_COLOR = { bg: '#FDF0EA', border: '#B85C38', text: '#B85C38', label: '最像我会做的' }
const WORST_COLOR = { bg: '#F3F4F6', border: '#9CA3AF', text: '#6B7280', label: '最不像' }

interface Props {
  onComplete: () => void
  onCancel: () => void
}

export function SjtQuiz({ onComplete, onCancel }: Props) {
  const [questions, setQuestions] = useState<SjtQuestion[]>([])
  const [sessionId, setSessionId] = useState('')
  const [answers, setAnswers] = useState<SjtAnswer[]>([])
  const [loading, setLoading] = useState(false)
  const [checking, setChecking] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [started, setStarted] = useState(false)
  const [currentIdx, setCurrentIdx] = useState(0)

  // On mount: check for existing in-progress session
  useEffect(() => {
    let mounted = true
    getSjtProgress()
      .then((progress) => {
        if (!mounted) return
        if (progress) {
          setQuestions(progress.questions)
          setSessionId(progress.session_id)
          setAnswers(progress.answers)
          setCurrentIdx(progress.current_idx)
          setStarted(true)
        }
        setChecking(false)
      })
      .catch(() => {
        if (mounted) setChecking(false)
      })
    return () => { mounted = false }
  }, [])

  const start = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await generateSjt()
      setQuestions(res.questions)
      setSessionId(res.session_id)
      setStarted(true)
      setCurrentIdx(0)
    } catch (e) {
      setError(e instanceof Error ? e.message : '生成失败')
    } finally {
      setLoading(false)
    }
  }

  const getAnswer = useCallback(
    (qid: string) => answers.find((a) => a.question_id === qid),
    [answers],
  )

  const setBest = (qid: string, oid: string) => {
    setAnswers((prev) => {
      const existing = prev.find((a) => a.question_id === qid)
      if (existing) {
        if (existing.worst === oid) {
          return prev.map((a) => (a.question_id === qid ? { ...a, best: oid, worst: '' } : a))
        }
        return prev.map((a) => (a.question_id === qid ? { ...a, best: oid } : a))
      }
      return [...prev, { question_id: qid, best: oid, worst: '' }]
    })
  }

  const setWorst = (qid: string, oid: string) => {
    setAnswers((prev) => {
      const existing = prev.find((a) => a.question_id === qid)
      if (existing) {
        if (existing.best === oid) {
          return prev.map((a) => (a.question_id === qid ? { ...a, best: '', worst: oid } : a))
        }
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

  const goNext = () => {
    if (currentIdx < questions.length - 1) {
      setCurrentIdx(currentIdx + 1)
    }
  }

  const goPrev = () => {
    if (currentIdx > 0) {
      setCurrentIdx(currentIdx - 1)
    }
  }

  // Auto-save progress
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => {
    if (!sessionId || !started) return
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      saveSjtProgress(sessionId, answers, currentIdx).catch(() => {})
    }, 800)
    return () => {
      if (saveTimer.current) clearTimeout(saveTimer.current)
    }
  }, [answers, currentIdx, sessionId, started])

  const currentQ = questions[currentIdx]
  const currentAns = currentQ ? getAnswer(currentQ.id) : undefined
  const progress = questions.length > 0 ? ((currentIdx + 1) / questions.length) * 100 : 0
  const answeredCount = answers.filter((a) => a.best && a.worst).length

  /* ── Loading check ── */
  if (checking) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-6">
        <div className="w-8 h-8 rounded-full border-2 border-[var(--chestnut)] border-t-transparent animate-spin mb-4" />
        <p className="text-[13px]" style={{ ...sans, color: ink(3) }}>检查中…</p>
      </div>
    )
  }

  /* ── Start Screen ── */
  if (!started) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-6">
        {/* Decorative element */}
        <div className="relative w-20 h-20 mb-8">
          <motion.div
            className="absolute inset-0 rounded-full border-2 border-dashed"
            style={{ borderColor: 'var(--chestnut)', opacity: 0.2 }}
            animate={{ rotate: 360 }}
            transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
          />
          <div
            className="absolute inset-3 rounded-full flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #FDF5E8, #F5E6D0)' }}
          >
            <span className="text-2xl" style={{ ...serif, color: 'var(--chestnut)' }}>?</span>
          </div>
        </div>

        <h2
          className="text-center mb-3"
          style={{
            ...serif,
            fontSize: 'clamp(24px, 3vw, 32px)',
            fontWeight: 600,
            color: ink(1),
            lineHeight: 1.2,
          }}
        >
          情境小测
        </h2>

        <p
          className="text-center max-w-sm mb-2"
          style={{ ...sans, fontSize: '15px', color: ink(2), lineHeight: 1.7 }}
        >
          几个职场小场景，选最接近你真实反应的选项。
        </p>
        <p
          className="text-center max-w-sm mb-8"
          style={{ ...sans, fontSize: '13px', color: ink(3), lineHeight: 1.6 }}
        >
          没有标准答案，3 分钟即可完成。退出后进度会自动保存。
        </p>

        {error && (
          <p className="mb-4 text-[13px]" style={{ color: '#DC2626' }}>{error}</p>
        )}

        <div className="flex items-center gap-3">
          <motion.button
            onClick={start}
            disabled={loading}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="px-8 py-3 rounded-full text-[14px] font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            style={{ background: 'var(--chestnut)', ...sans }}
          >
            {loading ? '生成中…' : '开始评估'}
          </motion.button>
          <button
            onClick={onCancel}
            className="px-6 py-3 rounded-full text-[14px] font-medium transition-colors"
            style={{ color: ink(3), ...sans }}
          >
            取消
          </button>
        </div>
      </div>
    )
  }

  /* ── Quiz Screen ── */
  return (
    <div className="flex flex-col" style={{ minHeight: '420px' }}>
      {/* Progress bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-medium" style={{ ...sans, color: ink(3) }}>
            {currentIdx + 1} / {questions.length}
          </span>
          <span className="text-[11px]" style={{ ...sans, color: ink(3) }}>
            已答 {answeredCount} 题
          </span>
        </div>
        <div className="h-1 rounded-full overflow-hidden" style={{ background: 'var(--line)' }}>
          <motion.div
            className="h-full rounded-full"
            style={{ background: 'linear-gradient(90deg, var(--chestnut), #C4853F)' }}
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
          />
        </div>
      </div>

      {/* Question card */}
      <AnimatePresence mode="wait">
        {currentQ && (
          <motion.div
            key={currentQ.id}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="flex-1"
          >
            {/* Scenario */}
            <div
              className="rounded-xl p-6 mb-5"
              style={{
                background: 'linear-gradient(135deg, #FDF5E8, #F9F4EE)',
                border: '1px solid var(--line)',
              }}
            >
              <p
                className="mb-1"
                style={{
                  ...serif,
                  fontSize: 'clamp(18px, 2.4vw, 22px)',
                  fontWeight: 500,
                  color: ink(1),
                  lineHeight: 1.6,
                  fontStyle: 'italic',
                }}
              >
                "{currentQ.scenario}"
              </p>
            </div>

            {/* Selection mode legend */}
            <div className="flex items-center gap-4 mb-4">
              <div className="flex items-center gap-1.5">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ background: BEST_COLOR.bg, border: `2px solid ${BEST_COLOR.border}` }}
                />
                <span className="text-[11px] font-medium" style={{ ...sans, color: BEST_COLOR.text }}>
                  {BEST_COLOR.label}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ background: WORST_COLOR.bg, border: `2px solid ${WORST_COLOR.border}` }}
                />
                <span className="text-[11px] font-medium" style={{ ...sans, color: WORST_COLOR.text }}>
                  {WORST_COLOR.label}
                </span>
              </div>
            </div>

            {/* Options */}
            <div className="space-y-3">
              {currentQ.options.map((o) => {
                const isBest = currentAns?.best === o.id
                const isWorst = currentAns?.worst === o.id

                return (
                  <motion.div
                    key={o.id}
                    whileHover={{ scale: 1.005 }}
                    className="flex items-stretch gap-3 rounded-xl p-4 transition-all duration-200"
                    style={{
                      background: isBest ? BEST_COLOR.bg : isWorst ? WORST_COLOR.bg : 'var(--bg-card)',
                      border: `2px solid ${isBest ? BEST_COLOR.border : isWorst ? WORST_COLOR.border : 'var(--line)'}`,
                      boxShadow: isBest ? '0 2px 8px rgba(184, 92, 56, 0.12)' : isWorst ? '0 2px 8px rgba(156, 163, 175, 0.12)' : 'none',
                    }}
                  >
                    {/* Text */}
                    <span
                      className="flex-1 self-center text-[14px] leading-relaxed"
                      style={{
                        ...sans,
                        color: isBest ? BEST_COLOR.text : isWorst ? WORST_COLOR.text : ink(2),
                        fontWeight: isBest || isWorst ? 500 : 400,
                      }}
                    >
                      {o.text}
                    </span>

                    {/* Right side — Best + Worst stacked */}
                    <div className="shrink-0 flex flex-col gap-2">
                      {/* Best */}
                      <button
                        onClick={() => setBest(currentQ.id, o.id)}
                        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg cursor-pointer transition-colors"
                        style={{
                          background: isBest ? BEST_COLOR.border : 'transparent',
                          border: `1.5px solid ${isBest ? BEST_COLOR.border : 'var(--line)'}`,
                        }}
                        title={BEST_COLOR.label}
                      >
                        <div
                          className="w-4 h-4 rounded-full flex items-center justify-center"
                          style={{
                            border: `2px solid ${isBest ? 'white' : 'var(--line)'}`,
                            background: isBest ? 'white' : 'transparent',
                          }}
                        >
                          {isBest && (
                            <motion.div
                              initial={{ scale: 0 }}
                              animate={{ scale: 1 }}
                              className="w-2 h-2 rounded-full"
                              style={{ background: BEST_COLOR.border }}
                            />
                          )}
                        </div>
                        <span className="text-[11px] font-medium whitespace-nowrap" style={{ color: isBest ? 'white' : ink(3) }}>
                          最像
                        </span>
                      </button>

                      {/* Worst */}
                      <button
                        onClick={() => setWorst(currentQ.id, o.id)}
                        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg cursor-pointer transition-colors"
                        style={{
                          background: isWorst ? WORST_COLOR.border : 'transparent',
                          border: `1.5px solid ${isWorst ? WORST_COLOR.border : 'var(--line)'}`,
                        }}
                        title={WORST_COLOR.label}
                      >
                        <div
                          className="w-4 h-4 rounded-full flex items-center justify-center"
                          style={{
                            border: `2px solid ${isWorst ? 'white' : 'var(--line)'}`,
                            background: isWorst ? 'white' : 'transparent',
                          }}
                        >
                          {isWorst && (
                            <motion.span
                              initial={{ scale: 0 }}
                              animate={{ scale: 1 }}
                              className="text-[9px] font-bold leading-none"
                              style={{ color: WORST_COLOR.border }}
                            >
                              ×
                            </motion.span>
                          )}
                        </div>
                        <span className="text-[11px] font-medium whitespace-nowrap" style={{ color: isWorst ? 'white' : ink(3) }}>
                          最不像
                        </span>
                      </button>
                    </div>
                  </motion.div>
                )
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Navigation */}
      <div className="flex items-center justify-between mt-6 pt-4" style={{ borderTop: '1px solid var(--line)' }}>
        <button
          onClick={currentIdx === 0 ? onCancel : goPrev}
          className="px-5 py-2.5 rounded-full text-[13px] font-medium transition-colors"
          style={{ color: ink(3), ...sans }}
        >
          {currentIdx === 0 ? '取消' : '上一题'}
        </button>

        <div className="flex items-center gap-2">
          {/* Question dots */}
          {questions.map((_, i) => (
            <button
              key={i}
              onClick={() => setCurrentIdx(i)}
              className="w-2 h-2 rounded-full transition-all duration-200"
              style={{
                background: i === currentIdx ? 'var(--chestnut)' : i < currentIdx && answers.find((a) => a.question_id === questions[i]?.id && a.best && a.worst) ? 'var(--moss)' : 'var(--line)',
                transform: i === currentIdx ? 'scale(1.3)' : 'scale(1)',
              }}
            />
          ))}
        </div>

        {currentIdx === questions.length - 1 ? (
          <motion.button
            onClick={handleSubmit}
            disabled={loading || answeredCount < questions.length}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="px-6 py-2.5 rounded-full text-[13px] font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-40"
            style={{ background: 'var(--chestnut)', ...sans }}
          >
            {loading ? '提交中…' : '提交'}
          </motion.button>
        ) : (
          <motion.button
            onClick={goNext}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="px-6 py-2.5 rounded-full text-[13px] font-medium transition-colors"
            style={{
              background: currentAns?.best && currentAns?.worst ? 'var(--chestnut)' : 'var(--line)',
              color: currentAns?.best && currentAns?.worst ? 'white' : ink(3),
              ...sans,
            }}
          >
            下一题
          </motion.button>
        )}
      </div>

      {error && (
        <p className="mt-3 text-[13px] text-center" style={{ color: '#DC2626' }}>{error}</p>
      )}
    </div>
  )
}
