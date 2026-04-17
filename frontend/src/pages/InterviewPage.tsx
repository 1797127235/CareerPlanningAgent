import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ChevronRight,
  ChevronLeft,
  ChevronDown,
  Loader2,
  CheckCircle2,
  Circle,
  RotateCcw,
  Mic,
  Trash2,
} from 'lucide-react'
import { rawFetch } from '@/api/client'

const ease = [0.23, 1, 0.32, 1] as const

interface SpeechRecognitionAlternative {
  readonly transcript: string
  readonly confidence: number
}

interface SpeechRecognitionResult {
  readonly length: number
  readonly isFinal: boolean
  item(index: number): SpeechRecognitionAlternative
  [index: number]: SpeechRecognitionAlternative
}

interface SpeechRecognitionResultList {
  readonly length: number
  item(index: number): SpeechRecognitionResult
  [index: number]: SpeechRecognitionResult
}

interface SpeechRecognitionEvent extends Event {
  readonly resultIndex: number
  readonly results: SpeechRecognitionResultList
}

interface SpeechRecognition extends EventTarget {
  lang: string
  continuous: boolean
  interimResults: boolean
  onresult: ((this: SpeechRecognition, ev: SpeechRecognitionEvent) => void) | null
  onend: ((this: SpeechRecognition, ev: Event) => void) | null
  onerror: ((this: SpeechRecognition, ev: Event) => void) | null
  start(): void
  stop(): void
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognition
    webkitSpeechRecognition: new () => SpeechRecognition
  }
}

/* ── Types ── */

interface Question {
  id: string
  type: 'technical' | 'behavioral' | 'scenario' | string
  question: string
  focus_area: string
  difficulty: string
}

interface Answer {
  question_id: string
  answer: string
}

interface PerQuestionEval {
  question_id: string
  score: number
  strengths: string[]
  improvements: string[]
  suggested_answer: string
}

interface Evaluation {
  overall_score: number
  overall_comment: string
  per_question: PerQuestionEval[]
  skill_gaps: string[]
  tips: string[]
}

function normalizeEvaluation(raw: Record<string, unknown>): Evaluation {
  const pq = (raw.per_question ?? raw.reviews ?? []) as PerQuestionEval[]
  return {
    overall_score: (raw.overall_score as number) ?? 0,
    overall_comment: (raw.overall_comment ?? raw.summary ?? '') as string,
    per_question: pq,
    skill_gaps: (raw.skill_gaps ?? []) as string[],
    tips: (raw.tips ?? []) as string[],
  }
}

interface InterviewHistoryItem {
  id: number
  target_role: string
  status: string
  score: number | null
  created_at: string
}

/* ── Helpers ── */

function scoreColor(s: number) {
  return s >= 80 ? 'text-emerald-600' : s >= 60 ? 'text-blue-600' : s >= 40 ? 'text-amber-600' : 'text-red-500'
}

const typeColors: Record<string, { bg: string; text: string }> = {
  technical: { bg: 'bg-blue-50', text: 'text-blue-600' },
  behavioral: { bg: 'bg-purple-50', text: 'text-purple-600' },
  scenario: { bg: 'bg-amber-50', text: 'text-amber-600' },
}

function typeLabel(t: string) {
  const map: Record<string, string> = { technical: '技术题', behavioral: '行为题', scenario: '场景题' }
  return map[t] || t
}

/* ── Fake progress hook ── */
function useFakeProgress(isActive: boolean) {
  const [step, setStep] = useState(0)
  useEffect(() => {
    if (!isActive) { setStep(0); return }
    setStep(0)
    const t1 = setTimeout(() => setStep(1), 3000)
    const t2 = setTimeout(() => setStep(2), 6000)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [isActive])
  return step
}

/* ── Speech recognition hook ── */
function useSpeechRecognition(onResult: (text: string) => void) {
  const [isListening, setIsListening] = useState(false)
  const recognitionRef = useRef<SpeechRecognition | null>(null)

  const isSupported = typeof window !== 'undefined' &&
    ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)

  const start = useCallback(() => {
    if (!isSupported) return
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    const recognition = new SR()
    recognition.lang = 'zh-CN'
    recognition.continuous = true
    recognition.interimResults = false

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let newText = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          newText += event.results[i][0].transcript
        }
      }
      if (newText) onResult(newText)
    }

    recognition.onend = () => setIsListening(false)
    recognition.onerror = () => setIsListening(false)

    recognitionRef.current = recognition
    recognition.start()
    setIsListening(true)
  }, [isSupported, onResult])

  const stop = useCallback(() => {
    recognitionRef.current?.stop()
    setIsListening(false)
  }, [])

  return { isListening, isSupported, start, stop }
}

/* ── Typing placeholder hook ── */
function useTypingPlaceholder(
  items: string[],
  { typeSpeed = 100, eraseSpeed = 50, pauseMs = 2000 } = {}
) {
  const [text, setText] = useState('')
  const [isActive, setIsActive] = useState(true)

  useEffect(() => {
    if (!isActive || items.length === 0) return

    let itemIndex = 0
    let charIndex = 0
    let isErasing = false
    let timer: ReturnType<typeof setTimeout>

    const tick = () => {
      const current = items[itemIndex]

      if (!isErasing) {
        charIndex++
        setText(current.slice(0, charIndex))
        if (charIndex >= current.length) {
          isErasing = true
          timer = setTimeout(tick, pauseMs)
          return
        }
        timer = setTimeout(tick, typeSpeed)
      } else {
        charIndex--
        setText(current.slice(0, charIndex))
        if (charIndex <= 0) {
          isErasing = false
          itemIndex = (itemIndex + 1) % items.length
          timer = setTimeout(tick, typeSpeed * 2)
          return
        }
        timer = setTimeout(tick, eraseSpeed)
      }
    }

    timer = setTimeout(tick, 500)
    return () => clearTimeout(timer)
  }, [isActive, items, typeSpeed, eraseSpeed, pauseMs])

  return { text, stop: () => setIsActive(false), restart: () => setIsActive(true) }
}

/* ═══════════════════════════════════════════════
   InterviewPage
   ═══════════════════════════════════════════════ */

export default function InterviewPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [phase, setPhase] = useState<'setup' | 'interviewing' | 'evaluating' | 'results'>('setup')

  // Setup
  const [targetRole, setTargetRole] = useState('')
  const [jdText, setJdText] = useState('')
  const [showJd, setShowJd] = useState(false)
  const [showAllHistory, setShowAllHistory] = useState(false)

  // Interviewing
  const [interviewId, setInterviewId] = useState<number | null>(null)
  const [questions, setQuestions] = useState<Question[]>([])
  const [answers, setAnswers] = useState<Answer[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [currentAnswer, setCurrentAnswer] = useState('')

  // Results
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null)

  // History
  const { data: history } = useQuery<InterviewHistoryItem[]>({
    queryKey: ['interview-history'],
    queryFn: () => rawFetch('/interview/history'),
    staleTime: 30_000,
  })

  const startMutation = useMutation({
    mutationFn: (body: { target_role: string; jd_text: string }) =>
      rawFetch<{ id: number; questions: Question[] }>('/interview/start', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: (data) => {
      setInterviewId(data.id)
      setQuestions(data.questions)
      setAnswers(data.questions.map((q) => ({ question_id: q.id, answer: '' })))
      setCurrentIndex(0)
      setCurrentAnswer('')
      setPhase('interviewing')
      qc.invalidateQueries({ queryKey: ['interview-history'] })
    },
  })

  const submitMutation = useMutation({
    mutationFn: (body: { answers: Answer[] }) =>
      rawFetch<Record<string, unknown>>(`/interview/${interviewId}/submit`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: (data) => {
      setEvaluation(normalizeEvaluation(data))
      setPhase('results')
      qc.invalidateQueries({ queryKey: ['interview-history'] })
    },
  })

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation()
    await rawFetch(`/interview/${id}`, { method: 'DELETE' })
    qc.invalidateQueries({ queryKey: ['interview-history'] })
  }

  const fakeStep = useFakeProgress(phase === 'evaluating')

  const { isListening, isSupported, start, stop } = useSpeechRecognition(
    useCallback((text: string) => {
      setCurrentAnswer((prev) => prev + text)
    }, [])
  )

  const typingItems = useMemo(() => ['输入你想面试的岗位...', '后端工程师', '产品经理', '算法工程师', '前端开发', '数据分析师'], [])
  const typingPlaceholder = useTypingPlaceholder(typingItems, { typeSpeed: 80, eraseSpeed: 40, pauseMs: 1500 })

  useEffect(() => {
    if (phase === 'interviewing' && questions.length > 0) {
      setAnswers((prev) => {
        const next = [...prev]
        next[currentIndex] = { question_id: questions[currentIndex].id, answer: currentAnswer }
        return next
      })
    }
  }, [currentAnswer, currentIndex, phase, questions])

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex((i) => i + 1)
      setCurrentAnswer(answers[currentIndex + 1]?.answer || '')
    }
  }

  const handlePrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex((i) => i - 1)
      setCurrentAnswer(answers[currentIndex - 1]?.answer || '')
    }
  }

  const handleSubmit = () => {
    const finalAnswers = answers.map((a, i) =>
      i === currentIndex ? { ...a, answer: currentAnswer } : a
    )
    setAnswers(finalAnswers)
    setPhase('evaluating')
    submitMutation.mutate({ answers: finalAnswers })
  }

  const handleRestart = () => {
    setPhase('setup')
    setTargetRole('')
    setJdText('')
    setShowJd(false)
    setShowAllHistory(false)
    setInterviewId(null)
    setQuestions([])
    setAnswers([])
    setCurrentIndex(0)
    setCurrentAnswer('')
    setEvaluation(null)
  }

  const handleLoadHistory = async (id: number) => {
    const data = await rawFetch<{
      id: number
      target_role: string
      status: string
      questions: Question[]
      answers: Answer[]
      evaluation: Record<string, unknown> | null
    }>(`/interview/${id}`)
    if (data.status === 'evaluated' && data.evaluation) {
      setInterviewId(data.id)
      setTargetRole(data.target_role)
      setQuestions(data.questions)
      setAnswers(data.answers)
      setEvaluation(normalizeEvaluation(data.evaluation as Record<string, unknown>))
      setPhase('results')
    } else if (data.status === 'created') {
      setInterviewId(data.id)
      setTargetRole(data.target_role)
      setQuestions(data.questions)
      setAnswers(data.questions.map((q) => ({ question_id: q.id, answer: '' })))
      setCurrentIndex(0)
      setCurrentAnswer('')
      setPhase('interviewing')
    }
  }

  /* ── Phase: Setup ── */
  if (phase === 'setup') {
    const hasHistory = history && history.length > 0
    const recentRoles = hasHistory
      ? Array.from(new Set(history!.map((h) => h.target_role))).slice(0, 5)
      : []
    const completedHistory = history?.filter((h) => h.score !== null) || []
    const avgScore = completedHistory.length > 0
      ? Math.round(completedHistory.reduce((a, b) => a + (b.score || 0), 0) / completedHistory.length)
      : 0
    const displayHistory = hasHistory
      ? showAllHistory
        ? history!
        : history!.slice(0, 9)
      : []

    return (
      <div className="h-full w-full overflow-y-auto">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease }}
          className={`px-6 ${hasHistory ? 'max-w-[960px] mx-auto py-8' : 'max-w-[640px] mx-auto min-h-full flex flex-col justify-center py-12'}`}
        >
          {/* Title */}
          <div className={hasHistory ? 'flex items-center justify-between mb-6' : 'mb-12'}>
            <div>
              <h1 className={`font-bold text-slate-900 tracking-tight ${hasHistory ? 'text-[28px]' : 'text-[36px]'}`}>
                模拟面试
              </h1>
              {hasHistory ? (
                <span className="text-[13px] text-slate-400 tabular-nums">
                  共 {history!.length} 次 · 均分 {avgScore}
                </span>
              ) : (
                <p className="text-[15px] text-slate-400 mt-2">
                  AI 面试官根据你的简历出题，逐题评分
                </p>
              )}
            </div>
          </div>

          {/* Start interview block */}
          <div className={hasHistory ? 'rounded-xl border border-slate-200/60 bg-white/50 p-6' : ''}>
            {recentRoles.length > 0 && (
              <>
                <p className="text-[13px] text-slate-500 mb-3">最近练过</p>
                <div className="flex flex-wrap gap-2">
                  {recentRoles.map((role) => {
                    const active = targetRole === role
                    return (
                      <button
                        key={role}
                        onClick={() => setTargetRole(role)}
                        className={`px-3 py-1.5 rounded-lg text-[13px] font-medium border transition-all duration-200 cursor-pointer ${
                          active
                            ? 'border-blue-400 bg-blue-50 text-blue-700 scale-[1.02]'
                            : 'border-slate-200/60 bg-white text-slate-700 hover:border-blue-300 hover:bg-blue-50/50 hover:scale-[1.03] active:scale-[0.97]'
                        }`}
                      >
                        {role}
                      </button>
                    )
                  })}
                </div>
                <div className="flex items-center gap-3 my-4">
                  <div className="flex-1 h-px bg-slate-200/60"></div>
                  <span className="text-[12px] text-slate-400">或</span>
                  <div className="flex-1 h-px bg-slate-200/60"></div>
                </div>
              </>
            )}

            <div className="relative">
              <input
                type="text"
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                onFocus={() => typingPlaceholder.stop()}
                onBlur={() => { if (!targetRole) typingPlaceholder.restart() }}
                className={`w-full rounded-lg border border-slate-200/60 bg-white/50 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300/60 transition-all ${
                  hasHistory ? 'px-4 py-2.5 text-[14px]' : 'px-5 py-4 text-[16px]'
                }`}
              />
              {/* Typing placeholder overlay */}
              {!targetRole && !hasHistory && (
                <div className="absolute inset-0 flex items-center pointer-events-none">
                  <span className={`text-slate-300 ${hasHistory ? 'px-4 text-[14px]' : 'px-5 text-[16px]'}`}>
                    {typingPlaceholder.text}
                    <span className="inline-block w-px h-[1.1em] bg-slate-300 ml-0.5 animate-pulse align-middle" />
                  </span>
                </div>
              )}
            </div>

            {!hasHistory && (
              <div className="flex flex-wrap gap-2 mt-4">
                {['后端工程师', '前端开发', '产品经理', '算法工程师', '数据分析', '测试开发'].map((role) => (
                  <button
                    key={role}
                    onClick={() => setTargetRole(role)}
                    className={`px-3 py-1.5 rounded-lg text-[13px] font-medium border transition-all duration-200 cursor-pointer ${
                      targetRole === role
                        ? 'border-blue-400 bg-blue-50 text-blue-700'
                        : 'border-slate-200/60 bg-white/80 text-slate-500 hover:border-blue-300 hover:bg-blue-50/50 hover:text-slate-700'
                    }`}
                  >
                    {role}
                  </button>
                ))}
              </div>
            )}

            <div className="mt-3">
              {!showJd ? (
                <button
                  onClick={() => setShowJd(true)}
                  className="flex items-center gap-1 text-[13px] text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
                >
                  <ChevronRight className="w-3.5 h-3.5" />
                  附加 JD（可选，让题目更有针对性）
                </button>
              ) : (
                <div>
                  <button
                    onClick={() => setShowJd(false)}
                    className="flex items-center gap-1 text-[13px] text-slate-400 hover:text-slate-600 transition-colors cursor-pointer mb-2"
                  >
                    <ChevronDown className="w-3.5 h-3.5" />
                    附加 JD（可选）
                  </button>
                  <textarea
                    value={jdText}
                    onChange={(e) => setJdText(e.target.value)}
                    placeholder="粘贴目标岗位的招聘要求，AI 会据此调整题目方向..."
                    rows={3}
                    className="w-full px-4 py-3 rounded-lg border border-slate-200/60 bg-white/50 text-[14px] text-slate-800 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300/60 transition-all resize-none"
                  />
                </div>
              )}
            </div>

            <div className={`${hasHistory ? 'flex justify-end mt-5' : 'mt-10'}`}>
              <button
                onClick={() => startMutation.mutate({ target_role: targetRole, jd_text: jdText })}
                disabled={!targetRole.trim() || startMutation.isPending}
                className={`relative overflow-hidden rounded-lg text-white font-bold transition-all duration-300 cursor-pointer ${
                  startMutation.isPending
                    ? 'bg-blue-700 cursor-wait'
                    : 'bg-blue-600 hover:bg-blue-700 hover:-translate-y-0.5 hover:shadow-md active:translate-y-0 active:shadow-none active:scale-[0.98]'
                } disabled:opacity-30 disabled:hover:translate-y-0 disabled:hover:shadow-none disabled:cursor-not-allowed ${
                  hasHistory ? 'px-6 py-2.5 text-[14px]' : 'w-full py-4 text-[15px]'
                }`}
              >
                {/* Progress bar inside button */}
                {startMutation.isPending && (
                  <motion.div
                    initial={{ width: '0%' }}
                    animate={{ width: '100%' }}
                    transition={{ duration: 15, ease: 'linear' }}
                    className="absolute inset-y-0 left-0 bg-blue-500/30"
                  />
                )}
                <span className="relative z-10">
                  {startMutation.isPending
                    ? '正在生成题目...'
                    : hasHistory
                    ? '开始面试'
                    : '开始面试 · 5道题 · 约15分钟'}
                </span>
              </button>
            </div>

            {startMutation.isError && (
              <p className="text-[13px] text-red-600 mt-3">
                {startMutation.error instanceof Error ? startMutation.error.message : '题目生成失败'}
              </p>
            )}
          </div>

          {/* Practice records */}
          {hasHistory && (
            <div className="mt-8">
              <h2 className="text-[15px] font-semibold text-slate-700 mb-4">练习记录</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {displayHistory.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => handleLoadHistory(item.id)}
                    className="relative group text-left rounded-lg border border-slate-200/60 bg-white/50 p-4 hover:bg-white/70 hover:border-slate-300/60 hover:-translate-y-0.5 hover:shadow-sm transition-all duration-200 cursor-pointer"
                  >
                    <button
                      onClick={(e) => handleDelete(item.id, e)}
                      className="absolute top-2 right-2 p-1.5 rounded-md text-slate-300 opacity-0 group-hover:opacity-100 hover:text-red-500 hover:bg-red-50 transition-all cursor-pointer"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                    <p className="text-[14px] font-semibold text-slate-700 truncate pr-6">
                      {item.target_role}
                    </p>
                    <p className="text-[12px] text-slate-400 mt-0.5">
                      {item.created_at.slice(5, 10).replace('-', '/')}
                    </p>
                    {item.score !== null ? (
                      <p className={`text-[28px] font-black tabular-nums mt-3 mb-2 ${scoreColor(item.score)}`}>
                        {item.score}
                      </p>
                    ) : (
                      <span className="inline-block text-[12px] text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full font-medium mt-3 mb-2">
                        未完成
                      </span>
                    )}
                  </div>
                ))}
              </div>
              {history!.length > 9 && !showAllHistory && (
                <div className="mt-4">
                  <button
                    onClick={() => setShowAllHistory(true)}
                    className="text-[13px] text-slate-500 hover:text-slate-700 transition-colors cursor-pointer"
                  >
                    查看更多
                  </button>
                </div>
              )}
            </div>
          )}
        </motion.div>
      </div>
    )
  }

  /* ── Phase: Interviewing ── */
  if (phase === 'interviewing' && questions.length > 0) {
    const q = questions[currentIndex]
    const tc = typeColors[q.type] || { bg: 'bg-slate-50', text: 'text-slate-600' }
    const pct = ((currentIndex + 1) / questions.length) * 100
    const isLast = currentIndex === questions.length - 1

    return (
      <div className="flex flex-col h-full w-full">
        {/* Top progress bar */}
        <div className="w-full h-1.5 bg-slate-100">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.3, ease }}
            className="h-full bg-blue-500"
          />
        </div>

        <div className="flex-1 overflow-y-auto">
          <div className="max-w-[720px] mx-auto px-6 py-6">
            {/* Header row */}
            <div className="flex items-center justify-between mb-6">
              <button
                onClick={handleRestart}
                className="text-[13px] text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
              >
                退出
              </button>
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-bold text-slate-800">
                  {currentIndex + 1} / {questions.length}
                </span>
                <span className={`text-[12px] font-medium px-2 py-0.5 rounded-full ${tc.bg} ${tc.text}`}>
                  {typeLabel(q.type)}
                </span>
              </div>
            </div>

            <motion.div
              key={currentIndex}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, ease }}
            >
              {/* Question */}
              <div className="pb-5 border-b border-slate-200/50">
                <h2 className="text-[18px] font-bold text-slate-900 leading-[1.7]">
                  {q.question}
                </h2>
                <p className="text-[13px] text-slate-400 mt-3">
                  考察：{q.focus_area} · {q.difficulty}
                </p>
              </div>

              {/* Answer area */}
              <div className="pt-5">
                <textarea
                  value={currentAnswer}
                  onChange={(e) => setCurrentAnswer(e.target.value)}
                  placeholder="在这里写下你的回答..."
                  rows={10}
                  className="w-full bg-transparent border-0 text-[15px] text-slate-700 placeholder:text-slate-300 focus:outline-none focus:ring-0 resize-none leading-relaxed"
                />
                <div className="flex items-center mt-3">
                  {isSupported && (
                    <button
                      onClick={isListening ? stop : start}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[13px] font-medium transition-all cursor-pointer ${
                        isListening
                          ? 'bg-red-50 text-red-600 border border-red-200'
                          : 'bg-slate-50 text-slate-500 border border-slate-200/60 hover:bg-slate-100'
                      }`}
                    >
                      <Mic className={`w-3.5 h-3.5 ${isListening ? 'animate-pulse' : ''}`} />
                      {isListening ? '停止录音' : '语音输入'}
                    </button>
                  )}
                  <p className="text-[12px] text-slate-400 ml-auto">
                    {currentAnswer.length} 字
                  </p>
                </div>
              </div>

              {/* Navigation */}
              <div className="flex items-center justify-between mt-6">
                <button
                  onClick={handlePrev}
                  disabled={currentIndex === 0}
                  className="flex items-center gap-1 text-[13px] font-semibold text-slate-500 hover:text-slate-700 transition-colors disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                >
                  <ChevronLeft className="w-4 h-4" />
                  上一题
                </button>

                <div className="flex flex-col items-end gap-2">
                  {isLast && (
                    <span className="text-[12px] text-slate-400">
                      确认提交后将由 AI 面试官评估
                    </span>
                  )}
                  {isLast ? (
                    <button
                      onClick={handleSubmit}
                      className="flex items-center gap-1 px-6 py-2.5 rounded-xl bg-emerald-600 text-white text-[14px] font-bold hover:bg-emerald-700 active:scale-[0.98] transition-all cursor-pointer"
                    >
                      提交全部答案
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  ) : (
                    <button
                      onClick={handleNext}
                      className="flex items-center gap-1 px-6 py-2.5 rounded-xl bg-blue-600 text-white text-[14px] font-bold hover:bg-blue-700 active:scale-[0.98] transition-all cursor-pointer"
                    >
                      下一题
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    )
  }

  /* ── Phase: Evaluating ── */
  if (phase === 'evaluating') {
    return (
      <div className="flex flex-col items-center justify-center h-full w-full px-4">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease }}
          className="max-w-[400px] w-full"
        >
          <h2 className="text-[18px] font-bold text-slate-800 mb-8">正在评估...</h2>

          <div className="space-y-4">
            <div className="flex items-center gap-3">
              {fakeStep >= 1 ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
              ) : (
                <Loader2 className="w-5 h-5 animate-spin text-blue-500 shrink-0" />
              )}
              <span className={fakeStep >= 1 ? 'text-[13px] text-slate-600' : 'text-[13px] text-slate-800 font-semibold'}>
                技术题回答分析
              </span>
              {fakeStep >= 1 && <span className="text-[12px] text-emerald-600 ml-auto">已完成</span>}
            </div>

            <div className="flex items-center gap-3">
              {fakeStep >= 2 ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
              ) : fakeStep >= 1 ? (
                <Loader2 className="w-5 h-5 animate-spin text-blue-500 shrink-0" />
              ) : (
                <Circle className="w-5 h-5 text-slate-200 shrink-0" />
              )}
              <span className={
                fakeStep >= 2 ? 'text-[13px] text-slate-600' :
                fakeStep >= 1 ? 'text-[13px] text-slate-800 font-semibold' :
                'text-[13px] text-slate-400'
              }>
                行为题 STAR 结构检查
              </span>
              {fakeStep >= 2 && <span className="text-[12px] text-emerald-600 ml-auto">已完成</span>}
              {fakeStep === 1 && <span className="text-[12px] text-blue-500 ml-auto">进行中...</span>}
            </div>

            <div className="flex items-center gap-3">
              {fakeStep >= 2 ? (
                <Loader2 className="w-5 h-5 animate-spin text-blue-500 shrink-0" />
              ) : (
                <Circle className="w-5 h-5 text-slate-200 shrink-0" />
              )}
              <span className={fakeStep >= 2 ? 'text-[13px] text-slate-800 font-semibold' : 'text-[13px] text-slate-400'}>
                综合评分与建议生成
              </span>
              {fakeStep >= 2 && <span className="text-[12px] text-blue-500 ml-auto">进行中...</span>}
            </div>
          </div>

          <p className="text-[12px] text-slate-400 mt-8">通常 15-30 秒</p>
        </motion.div>
      </div>
    )
  }

  /* ── Phase: Results ── */
  if (phase === 'results' && evaluation) {
    return (
      <div className="flex flex-col h-full w-full overflow-y-auto pb-12">
        <div className="max-w-[720px] mx-auto px-6 py-8 w-full">
          {/* Back button */}
          <motion.button
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
            onClick={handleRestart}
            className="flex items-center gap-1.5 text-[13px] text-slate-400 hover:text-slate-600 transition-colors cursor-pointer mb-6"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            返回模拟面试
          </motion.button>

          {/* Overall score */}
          {(() => {
            const ringColor = evaluation.overall_score >= 80
              ? 'text-emerald-500'
              : evaluation.overall_score >= 60
              ? 'text-blue-500'
              : evaluation.overall_score >= 40
              ? 'text-amber-500'
              : 'text-red-500'
            return (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5, ease }}
                className="relative flex items-center gap-8 mb-10"
              >
                {/* Subtle background glow behind score */}
                <motion.div
                  initial={{ opacity: 0, scale: 0.5 }}
                  animate={{ opacity: 0.15, scale: 1 }}
                  transition={{ delay: 0.3, duration: 1.2, ease }}
                  className={`absolute -left-8 -top-8 w-[200px] h-[200px] rounded-full blur-3xl pointer-events-none ${
                    evaluation.overall_score >= 80 ? 'bg-emerald-300'
                    : evaluation.overall_score >= 60 ? 'bg-blue-300'
                    : evaluation.overall_score >= 40 ? 'bg-amber-300'
                    : 'bg-red-300'
                  }`}
                />
                <AnimatedScore score={evaluation.overall_score} color={ringColor} />
                <div className="flex-1 min-w-0">
                  <p className="text-[15px] text-slate-600 leading-relaxed max-w-[420px]">
                    {evaluation.overall_comment}
                  </p>
                </div>
              </motion.div>
            )
          })()}

          {/* Per-question evaluations */}
          <div className="mb-8">
            <h3 className="text-[14px] font-semibold text-slate-700 mb-4">
              逐题评分
            </h3>
            <div className="space-y-3">
              {(evaluation.per_question || []).map((pq, idx) => (
                <QuestionEvalRow
                  key={pq.question_id}
                  eval={pq}
                  question={questions[idx] || { id: pq.question_id, type: 'technical', question: '', focus_area: '', difficulty: '' }}
                  answer={answers[idx]?.answer || ''}
                  index={idx}
                />
              ))}
            </div>
          </div>

          {/* Skill gaps + tips combined */}
          {((evaluation.skill_gaps?.length || 0) > 0 || (evaluation.tips?.length || 0) > 0) && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.6, duration: 0.45, ease }}
              className="flex flex-col sm:flex-row gap-8 mb-10"
            >
              {(evaluation.skill_gaps?.length || 0) > 0 && (
                <div className="flex-1">
                  <h3 className="text-[13px] font-bold text-slate-400 uppercase tracking-wider mb-3">
                    需要关注
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {evaluation.skill_gaps.map((sg) => (
                      <span
                        key={sg}
                        className="px-2.5 py-1 rounded-lg bg-amber-50 text-amber-700 text-[13px] font-medium border border-amber-100/60"
                      >
                        {sg}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {(evaluation.tips?.length || 0) > 0 && (
                <div className="flex-1">
                  <h3 className="text-[13px] font-bold text-slate-400 uppercase tracking-wider mb-3">
                    改进建议
                  </h3>
                  <ul className="space-y-2">
                    {evaluation.tips.map((tip, i) => (
                      <li key={i} className="text-[13px] text-slate-600 leading-relaxed">
                        {i + 1}. {tip}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </motion.div>
          )}

          {/* Bottom actions */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 2.0, duration: 0.4, ease }}
            className="flex items-center gap-4"
          >
            <button
              onClick={handleRestart}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-blue-600 text-white text-[14px] font-bold hover:bg-blue-700 hover:-translate-y-0.5 hover:shadow-md active:translate-y-0 active:shadow-none active:scale-[0.98] transition-all duration-200 cursor-pointer"
            >
              <RotateCcw className="w-4 h-4" />
              再来一次
            </button>
            <button
              onClick={handleRestart}
              className="text-[14px] text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
            >
              返回模拟面试
            </button>
          </motion.div>
        </div>
      </div>
    )
  }

  return null
}

/* ── Sub-component: AnimatedScore ── */

function AnimatedScore({ score, color }: { score: number; color: string }) {
  const [displayed, setDisplayed] = useState(0)
  const radius = 54
  const circumference = 2 * Math.PI * radius
  const progress = (displayed / 100) * circumference

  useEffect(() => {
    let frame: number
    const duration = 1200 // ms
    const start = performance.now()
    const animate = (now: number) => {
      const elapsed = now - start
      const t = Math.min(elapsed / duration, 1)
      // ease-out-quart
      const eased = 1 - Math.pow(1 - t, 4)
      setDisplayed(Math.round(eased * score))
      if (t < 1) frame = requestAnimationFrame(animate)
    }
    frame = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(frame)
  }, [score])

  return (
    <div className="relative w-[140px] h-[140px] shrink-0">
      <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
        {/* Background circle */}
        <circle
          cx="60" cy="60" r={radius}
          fill="none"
          stroke="currentColor"
          className="text-slate-100"
          strokeWidth="8"
        />
        {/* Progress circle */}
        <motion.circle
          cx="60" cy="60" r={radius}
          fill="none"
          stroke="currentColor"
          className={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference - progress }}
          transition={{ duration: 0.05, ease: 'linear' }}
        />
      </svg>
      {/* Score number in center */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-[42px] font-black tabular-nums leading-none ${color}`}>
          {displayed}
        </span>
        <span className="text-[11px] text-slate-400 mt-1">综合得分</span>
      </div>
    </div>
  )
}

/* ── Sub-component: CountUp ── */

function CountUp({ value, delay = 0 }: { value: number; delay?: number }) {
  const [displayed, setDisplayed] = useState(0)

  useEffect(() => {
    const timeout = setTimeout(() => {
      let frame: number
      const duration = 600
      const start = performance.now()
      const animate = (now: number) => {
        const elapsed = now - start
        const t = Math.min(elapsed / duration, 1)
        const eased = 1 - Math.pow(1 - t, 4)
        setDisplayed(Math.round(eased * value))
        if (t < 1) frame = requestAnimationFrame(animate)
      }
      frame = requestAnimationFrame(animate)
      return () => cancelAnimationFrame(frame)
    }, delay)
    return () => clearTimeout(timeout)
  }, [value, delay])

  return <>{displayed}</>
}

/* ── Sub-component: QuestionEvalRow ── */

function QuestionEvalRow({
  eval: ev,
  question,
  answer,
  index,
}: {
  eval: PerQuestionEval
  question: Question
  answer: string
  index: number
}) {
  const [showSuggested, setShowSuggested] = useState(false)
  const [showMyAnswer, setShowMyAnswer] = useState(false)
  const tc = typeColors[question.type] || { bg: 'bg-slate-50', text: 'text-slate-600' }

  // 分数色条颜色
  const barColor = ev.score >= 80
    ? 'bg-emerald-400'
    : ev.score >= 60
    ? 'bg-blue-400'
    : ev.score >= 40
    ? 'bg-amber-400'
    : 'bg-red-400'

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.6 + index * 0.15, duration: 0.45, ease }}
      className="rounded-xl border border-slate-200/60 bg-white/50 overflow-hidden hover:border-slate-300/60 hover:bg-white/70 hover:shadow-sm transition-all duration-200"
    >
      {/* 顶部分数色条 */}
      <div className="h-1 bg-slate-100">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${ev.score}%` }}
          transition={{ delay: 0.8 + index * 0.15, duration: 0.6, ease }}
          className={`h-full ${barColor}`}
        />
      </div>

      <div className="p-5">
        {/* Header line */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-[12px] font-bold text-slate-300 tabular-nums">
                {String(index + 1).padStart(2, '0')}
              </span>
              <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${tc.bg} ${tc.text}`}>
                {typeLabel(question.type)}
              </span>
              <span className="text-[11px] text-slate-400">
                {question.focus_area}
              </span>
            </div>
            <p className="text-[13px] text-slate-600 leading-relaxed line-clamp-2">
              {question.question}
            </p>
          </div>
          <span className={`text-[28px] font-black tabular-nums shrink-0 leading-none ${scoreColor(ev.score)}`}>
            <CountUp value={ev.score} delay={700 + index * 150} />
          </span>
        </div>

        {/* Strengths & Improvements */}
        {(ev.strengths.length > 0 || ev.improvements.length > 0) && (
          <div className="mt-4 pt-4 border-t border-slate-100">
            {ev.strengths.length > 0 && (
              <div className="space-y-1.5 mb-2">
                {ev.strengths.map((s, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <span className="text-emerald-500 text-[12px] mt-0.5 shrink-0">✓</span>
                    <p className="text-[13px] text-slate-600 leading-relaxed">{s}</p>
                  </div>
                ))}
              </div>
            )}
            {ev.improvements.length > 0 && (
              <div className="space-y-1.5">
                {ev.improvements.map((s, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <span className="text-amber-500 text-[12px] mt-0.5 shrink-0">△</span>
                    <p className="text-[13px] text-slate-600 leading-relaxed">{s}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* My answer toggle */}
        {answer && (
          <>
            <button
              onClick={() => setShowMyAnswer((v) => !v)}
              className="mt-4 flex items-center gap-1 text-[12px] font-semibold text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
            >
              <ChevronRight className={`w-3 h-3 transition-transform ${showMyAnswer ? 'rotate-90' : ''}`} />
              我的回答
            </button>
            <AnimatePresence>
              {showMyAnswer && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="mt-2 p-4 rounded-lg bg-blue-50/50 border border-blue-100/60 text-[13px] text-slate-600 leading-[1.8] whitespace-pre-wrap">
                    {answer}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </>
        )}

        {/* Suggested answer toggle */}
        <button
          onClick={() => setShowSuggested((v) => !v)}
          className="mt-4 flex items-center gap-1 text-[12px] font-semibold text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
        >
          <ChevronRight className={`w-3 h-3 transition-transform ${showSuggested ? 'rotate-90' : ''}`} />
          参考回答
        </button>
        <AnimatePresence>
          {showSuggested && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="mt-2 p-4 rounded-lg bg-slate-50/80 text-[13px] text-slate-600 leading-[1.8]">
                {ev.suggested_answer}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}
