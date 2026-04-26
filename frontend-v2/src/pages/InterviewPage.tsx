import { useState, useEffect, useRef, useCallback, useMemo, type ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'
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
  Cpu,
  Monitor,
  Server,
  Calculator,
  BarChart3,
  ShieldCheck,
  Bot,
} from 'lucide-react'
import { rawFetch } from '@/api/client'
import Navbar from '@/components/shared/Navbar'

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
  follow_ups?: string[]
}

interface FollowUpTurn {
  question: string
  answer: string
  source?: string
}

interface Answer {
  question_id: string
  answer: string
  follow_ups: FollowUpTurn[]
}

interface PerQuestionEval {
  question_id: string
  score: number
  strengths: string[]
  improvements: string[]
  suggested_answer: string
  follow_up_comment?: string
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

function buildAnswersFromQuestions(questions: Question[], existingAnswers: Answer[] = []): Answer[] {
  const answerMap = new Map(existingAnswers.map((item) => [item.question_id, item]))
  return questions.map((question) => {
    const existing = answerMap.get(question.id)
    return {
      question_id: question.id,
      answer: existing?.answer ?? '',
      follow_ups: (existing?.follow_ups ?? [])
        .filter((item) => item?.question)
        .map((item) => ({
          question: item.question,
          answer: item.answer ?? '',
          source: item.source ?? 'dynamic',
        })),
    }
  })
}

function findResumeIndex(answers: Answer[]) {
  const nextIndex = answers.findIndex((item) => {
    if (!item.answer.trim()) return true
    return (item.follow_ups || []).some((turn) => !turn.answer.trim())
  })
  return nextIndex === -1 ? Math.max(answers.length - 1, 0) : nextIndex
}

function countAnsweredFollowUps(answers: Answer[]) {
  return answers.reduce(
    (sum, item) => sum + (item.follow_ups || []).filter((turn) => turn.answer.trim()).length,
    0,
  )
}

function hasInterviewDraftContent(answers: Answer[]) {
  return answers.some((item) => item.answer.trim() || (item.follow_ups || []).some((turn) => turn.answer.trim()))
}

function normalizeTypeDistribution(questionCount: number, distribution: Record<string, number>) {
  const normalized = {
    technical: Math.max(Math.floor(distribution.technical || 0), 0),
    scenario: Math.max(Math.floor(distribution.scenario || 0), 0),
    behavioral: Math.max(Math.floor(distribution.behavioral || 0), 0),
  }

  let total = TYPE_KEYS.reduce((sum, key) => sum + normalized[key], 0)
  if (total <= 0) {
    normalized.technical = questionCount
    return normalized
  }

  if (total < questionCount) {
    normalized.technical += questionCount - total
    return normalized
  }

  let overflow = total - questionCount
  for (const key of TYPE_KEYS) {
    if (overflow <= 0) break
    const reducible = Math.min(normalized[key], overflow)
    normalized[key] -= reducible
    overflow -= reducible
  }

  total = TYPE_KEYS.reduce((sum, key) => sum + normalized[key], 0)
  if (total <= 0) {
    normalized.technical = questionCount
  }

  return normalized
}

interface InterviewHistoryItem {
  id: number
  target_role: string
  status: string
  score: number | null
  created_at: string
}

interface SavedInterviewDraft {
  interviewId: number
  targetRole: string
  answers: Answer[]
  currentIndex: number
}

const TYPE_KEYS = ['technical', 'scenario', 'behavioral'] as const
const INTERVIEW_DRAFT_KEY = 'interview_draft'

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

/* ── Loading steps hook for question generation ── */
function _resolveDirectionName(role: string): string {
  const r = role.toLowerCase()
  if (r.includes('c++') || r.includes('cpp')) return 'C++'
  if (r.includes('java')) return 'Java'
  if (r.includes('前端') || r.includes('react') || r.includes('vue') || r.includes('web')) return '前端'
  if (r.includes('算法') || r.includes('ai') || r.includes('machine learning')) return '算法'
  if (r.includes('产品') || r.includes('pm')) return '产品'
  if (r.includes('测试') || r.includes('qa')) return '测试'
  return ''
}

function useLoadingSteps(isActive: boolean, targetRole: string = '') {
  const dir = _resolveDirectionName(targetRole)
  const dirText = dir ? `${dir} ` : ''
  const steps = [
    '正在分析简历画像...',
    `正在匹配${dirText}方向题库...`,
    '正在生成技术面试题...',
    '正在组装个性化面试...',
    '马上就好...',
  ]
  const [index, setIndex] = useState(0)
  useEffect(() => {
    if (!isActive) { setIndex(0); return }
    setIndex(0)
    const interval = setInterval(() => {
      setIndex((prev) => (prev < steps.length - 1 ? prev + 1 : prev))
    }, 3000)
    return () => clearInterval(interval)
  }, [isActive])
  return steps[index]
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
  return (
    <main className="min-h-screen pt-[64px]" style={{ background: "var(--bg-paper)", color: "var(--ink-1)" }}>
      <Navbar />
      <_InterviewPage />
    </main>
  )
}

function _InterviewPage() {
  const [searchParams] = useSearchParams()
  const qc = useQueryClient()
  const [phase, setPhase] = useState<'setup' | 'interviewing' | 'evaluating' | 'results'>('setup')

  const clearInterviewSession = useCallback(() => {
    sessionStorage.removeItem('interview_generating')
    sessionStorage.removeItem('interview_id')
    sessionStorage.removeItem('interview_phase')
    sessionStorage.removeItem(INTERVIEW_DRAFT_KEY)
  }, [])

  // Setup
  const [targetRole, setTargetRole] = useState('')
  const [jdText, setJdText] = useState('')
  const [showJd, setShowJd] = useState(false)
  const [showAllHistory, setShowAllHistory] = useState(false)
  const [questionCount, setQuestionCount] = useState(5)
  const [typeDistribution, setTypeDistribution] = useState<Record<string, number>>({ technical: 3, scenario: 1, behavioral: 1 })

  // Auto-fill targetRole from URL query param (?role=xxx)
  useEffect(() => {
    const roleFromUrl = searchParams.get('role')
    if (roleFromUrl && !targetRole) {
      setTargetRole(roleFromUrl)
    }
  }, [searchParams])

  // Interviewing
  const [interviewId, setInterviewId] = useState<number | null>(null)
  const [questions, setQuestions] = useState<Question[]>([])
  const [answers, setAnswers] = useState<Answer[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [currentAnswer, setCurrentAnswer] = useState('')
  const [currentFollowUps, setCurrentFollowUps] = useState<FollowUpTurn[]>([])
  const [followUpError, setFollowUpError] = useState<string | null>(null)
  const [followUpInfo, setFollowUpInfo] = useState<string | null>(null)

  // Results
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const restoreInterviewState = useCallback((data: {
    id: number
    target_role: string
    status: string
    questions: Question[]
    answers?: Answer[]
    evaluation?: Record<string, unknown> | null
  }) => {
    const normalizedAnswers = buildAnswersFromQuestions(data.questions, data.answers || [])
    let nextAnswers = normalizedAnswers
    let nextIndex = findResumeIndex(normalizedAnswers)

    const draftRaw = sessionStorage.getItem(INTERVIEW_DRAFT_KEY)
    if (draftRaw && data.status !== 'evaluated') {
      try {
        const draft = JSON.parse(draftRaw) as SavedInterviewDraft
        if (draft.interviewId === data.id) {
          nextAnswers = buildAnswersFromQuestions(data.questions, draft.answers || [])
          nextIndex = Math.min(Math.max(draft.currentIndex || 0, 0), Math.max(data.questions.length - 1, 0))
        }
      } catch {
        sessionStorage.removeItem(INTERVIEW_DRAFT_KEY)
      }
    }

    setInterviewId(data.id)
    setTargetRole(data.target_role)
    setQuestions(data.questions)
    setAnswers(nextAnswers)
    setCurrentIndex(nextIndex)
    setCurrentAnswer(nextAnswers[nextIndex]?.answer || '')
    setCurrentFollowUps(nextAnswers[nextIndex]?.follow_ups || [])
    setSubmitError(null)
    setFollowUpError(null)
    setFollowUpInfo(null)

    if (data.status === 'evaluated' && data.evaluation) {
      setEvaluation(normalizeEvaluation(data.evaluation))
      setPhase('results')
      clearInterviewSession()
      return
    }

    setEvaluation(null)
    setPhase('interviewing')
    sessionStorage.setItem('interview_id', String(data.id))
    sessionStorage.setItem('interview_phase', 'interviewing')
  }, [clearInterviewSession])

  // History
  const { data: history } = useQuery<InterviewHistoryItem[]>({
    queryKey: ['interview-history'],
    queryFn: () => rawFetch('/interview/history'),
    staleTime: 30_000,
  })

  const startMutation = useMutation({
    mutationFn: (body: { target_role: string; jd_text: string; question_count: number; type_distribution: Record<string, number> }) =>
      rawFetch<{ id: number; questions: Question[] }>('/interview/start', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onMutate: () => {
      setSubmitError(null)
      sessionStorage.setItem('interview_generating', 'true')
    },
    onSuccess: (data) => {
      const initialAnswers = buildAnswersFromQuestions(data.questions)
      clearInterviewSession()
      sessionStorage.setItem('interview_id', String(data.id))
      sessionStorage.setItem('interview_phase', 'interviewing')
      setInterviewId(data.id)
      setQuestions(data.questions)
      setAnswers(initialAnswers)
      setCurrentIndex(0)
      setCurrentAnswer(initialAnswers[0]?.answer || '')
      setCurrentFollowUps(initialAnswers[0]?.follow_ups || [])
      setFollowUpError(null)
      setFollowUpInfo(null)
      setEvaluation(null)
      setPhase('interviewing')
      qc.invalidateQueries({ queryKey: ['interview-history'] })
    },
    onError: () => {
      sessionStorage.removeItem('interview_generating')
    },
  })

  const submitMutation = useMutation({
    mutationFn: (body: { answers: Answer[] }) =>
      rawFetch<Record<string, unknown>>(`/interview/${interviewId}/submit`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onMutate: () => {
      setSubmitError(null)
    },
    onSuccess: (data) => {
      clearInterviewSession()
      setEvaluation(normalizeEvaluation(data))
      setPhase('results')
      qc.invalidateQueries({ queryKey: ['interview-history'] })
    },
    onError: (error) => {
      setPhase('interviewing')
      setSubmitError(error instanceof Error ? error.message : '评估失败，请稍后重试')
    },
  })

  const followUpMutation = useMutation({
    mutationFn: (body: { question_id: string; answer: string; follow_ups: FollowUpTurn[] }) =>
      rawFetch<{ follow_up?: string; round: number; max_rounds: number; done: boolean }>(`/interview/${interviewId}/follow-up`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onMutate: () => {
      setFollowUpError(null)
      setFollowUpInfo(null)
    },
    onSuccess: (data) => {
      if (data.done || !data.follow_up) {
        setFollowUpInfo('这一题暂时没有更多值得追问的点了')
        return
      }
      const newTurn = { question: data.follow_up!, answer: '', source: 'dynamic' }
      setCurrentFollowUps((prev) => {
        const next = [...prev, newTurn]
        // Sync into answers so switching questions won't bleed over
        setAnswers((prevAnswers) =>
          prevAnswers.map((a, i) =>
            i === currentIndex ? { ...a, follow_ups: next } : a
          )
        )
        return next
      })
    },
    onError: (error) => {
      setFollowUpError(error instanceof Error ? error.message : '追问生成失败，请稍后重试')
    },
  })

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation()
    await rawFetch(`/interview/${id}`, { method: 'DELETE' })
    qc.invalidateQueries({ queryKey: ['interview-history'] })
  }

  const fakeStep = useFakeProgress(phase === 'evaluating')
  const loadingStep = useLoadingSteps(startMutation.isPending, targetRole)

  // Warn before browser refresh/close when generating or interviewing
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (startMutation.isPending || (phase === 'interviewing' && hasInterviewDraftContent(answers))) {
        e.preventDefault()
        e.returnValue = ''
      }
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [startMutation.isPending, phase, answers])

  // Restore state from sessionStorage on mount
  useEffect(() => {
    const savedId = sessionStorage.getItem('interview_id')
    const savedPhase = sessionStorage.getItem('interview_phase')
    const isGenerating = sessionStorage.getItem('interview_generating') === 'true'

    if (isGenerating && !startMutation.isPending && !interviewId) {
      const checkLatest = async () => {
        try {
          const latestHistory: InterviewHistoryItem[] = await rawFetch('/interview/history')
          const latest = latestHistory[0]
          if (latest && latest.status === 'created') {
            const data = await rawFetch<{
              id: number
              target_role: string
              status: string
              questions: Question[]
              answers?: Answer[]
              evaluation?: Record<string, unknown> | null
            }>(`/interview/${latest.id}`)
            if (data.questions && data.questions.length > 0) {
              restoreInterviewState(data)
            }
          }
        } catch {
          // ignore
        } finally {
          sessionStorage.removeItem('interview_generating')
        }
      }
      checkLatest()
      return
    }

    if (savedId && savedPhase === 'interviewing' && phase === 'setup') {
      const restore = async () => {
        try {
          const data = await rawFetch<{
            id: number
            target_role: string
            status: string
            questions: Question[]
            answers?: Answer[]
            evaluation?: Record<string, unknown> | null
          }>(`/interview/${savedId}`)
          if (data.questions && data.questions.length > 0) {
            restoreInterviewState(data)
          }
        } catch {
          clearInterviewSession()
        }
      }
      restore()
    }
  }, [clearInterviewSession, interviewId, phase, restoreInterviewState, startMutation.isPending])

  const { isListening, isSupported, start, stop } = useSpeechRecognition(
    useCallback((text: string) => {
      setCurrentAnswer((prev) => prev + text)
    }, [])
  )

  const typingItems = useMemo(() => ['输入你想面试的岗位...', '后端工程师', '产品经理', '算法工程师', '前端开发', '数据分析师'], [])
  const typingPlaceholder = useTypingPlaceholder(typingItems, { typeSpeed: 80, eraseSpeed: 40, pauseMs: 1500 })
  const assignedCount = useMemo(() => TYPE_KEYS.reduce((sum, key) => sum + (typeDistribution[key] || 0), 0), [typeDistribution])
  const normalizedTypeDistribution = useMemo(() => normalizeTypeDistribution(questionCount, typeDistribution), [questionCount, typeDistribution])
  const shouldAutoBalanceDistribution = assignedCount !== questionCount

  useEffect(() => {
    if (phase === 'interviewing' && questions.length > 0) {
      setAnswers((prev) => {
        const next = [...prev]
        next[currentIndex] = {
          question_id: questions[currentIndex].id,
          answer: currentAnswer,
          follow_ups: currentFollowUps,
        }
        return next
      })
    }
  }, [currentAnswer, currentFollowUps, currentIndex, phase, questions])

  useEffect(() => {
    if (phase !== 'interviewing' || !interviewId || questions.length === 0) return

    const persistedAnswers = answers.map((item, index) =>
      index === currentIndex ? { ...item, answer: currentAnswer, follow_ups: currentFollowUps } : item
    )

    const draft: SavedInterviewDraft = {
      interviewId,
      targetRole,
      answers: persistedAnswers,
      currentIndex,
    }

    sessionStorage.setItem('interview_id', String(interviewId))
    sessionStorage.setItem('interview_phase', 'interviewing')
    sessionStorage.setItem(INTERVIEW_DRAFT_KEY, JSON.stringify(draft))
  }, [answers, currentAnswer, currentFollowUps, currentIndex, interviewId, phase, questions.length, targetRole])

  // Track whether we've already auto-triggered follow-up for this (question, answer) combo
  const autoFollowUpTriggeredRef = useRef<Set<string>>(new Set())

  const handleGenerateFollowUp = (answer?: string, followUps?: FollowUpTurn[]) => {
    if (!interviewId || !questions[currentIndex]) return
    const ans = answer ?? currentAnswer
    const fus = followUps ?? currentFollowUps
    followUpMutation.mutate({
      question_id: questions[currentIndex].id,
      answer: ans,
      follow_ups: fus,
    })
  }

  // Auto-trigger follow-up when user finishes typing in main answer box (onBlur)
  const handleMainAnswerBlur = () => {
    if (!interviewId || !questions[currentIndex]) return
    const q = questions[currentIndex]
    const answerTrimmed = currentAnswer.trim()

    // Conditions: answer long enough, haven't reached max follow-ups, not already pending
    const hasUnfinishedFollowUp = currentFollowUps.length > 0 &&
      !currentFollowUps[currentFollowUps.length - 1]?.answer.trim()
    if (
      answerTrimmed.length < 30 ||
      currentFollowUps.length >= 2 ||
      hasUnfinishedFollowUp ||
      followUpMutation.isPending
    ) return

    // Deduplicate: don't re-trigger if answer + follow-up count hasn't changed
    const key = `${q.id}::${answerTrimmed.length}::${currentFollowUps.length}`
    if (autoFollowUpTriggeredRef.current.has(key)) return
    autoFollowUpTriggeredRef.current.add(key)

    handleGenerateFollowUp(currentAnswer, currentFollowUps)
  }

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      autoFollowUpTriggeredRef.current.clear()
      // Save current question state before switching
      setAnswers((prev) =>
        prev.map((a, i) =>
          i === currentIndex ? { ...a, answer: currentAnswer, follow_ups: currentFollowUps } : a
        )
      )
      const nextIdx = currentIndex + 1
      setCurrentIndex(nextIdx)
      setCurrentAnswer(answers[nextIdx]?.answer || '')
      setCurrentFollowUps(answers[nextIdx]?.follow_ups || [])
      setFollowUpError(null)
      setFollowUpInfo(null)
    }
  }

  const handlePrev = () => {
    if (currentIndex > 0) {
      autoFollowUpTriggeredRef.current.clear()
      // Save current question state before switching
      setAnswers((prev) =>
        prev.map((a, i) =>
          i === currentIndex ? { ...a, answer: currentAnswer, follow_ups: currentFollowUps } : a
        )
      )
      const prevIdx = currentIndex - 1
      setCurrentIndex(prevIdx)
      setCurrentAnswer(answers[prevIdx]?.answer || '')
      setCurrentFollowUps(answers[prevIdx]?.follow_ups || [])
      setFollowUpError(null)
      setFollowUpInfo(null)
    }
  }

  const handleSubmit = () => {
    if (submitMutation.isPending) return

    const finalAnswers = answers.map((a, i) =>
      i === currentIndex ? { ...a, answer: currentAnswer, follow_ups: currentFollowUps } : a
    )
    setSubmitError(null)
    setAnswers(finalAnswers)
    setPhase('evaluating')
    submitMutation.mutate({ answers: finalAnswers })
  }

  const handleRestart = () => {
    stop()
    clearInterviewSession()
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
    setCurrentFollowUps([])
    setFollowUpError(null)
    setFollowUpInfo(null)
    setEvaluation(null)
    setSubmitError(null)
  }

  const handleLoadHistory = async (id: number) => {
    const data = await rawFetch<{
      id: number
      target_role: string
      status: string
      questions: Question[]
      answers?: Answer[]
      evaluation: Record<string, unknown> | null
    }>(`/interview/${id}`)
    restoreInterviewState(data)
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
          className="px-6 max-w-[960px] mx-auto py-8"
        >
          {/* Title */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="font-bold text-[var(--ink-1)] tracking-tight text-[28px]">
                模拟面试
              </h1>
              <span className="text-[13px] text-[var(--ink-3)] tabular-nums">
                {hasHistory ? `共 ${history!.length} 次 · 均分 ${avgScore}` : 'AI 面试官根据你的简历出题，逐题评分'}
              </span>
            </div>
          </div>

          {/* Start interview block */}
          <div className="rounded-xl border border-[var(--line)]/60 bg-white/50 p-6">
            {recentRoles.length > 0 && (
              <>
                <p className="text-[13px] text-[var(--ink-2)] mb-3">最近练过</p>
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
                            : 'border-[var(--line)]/60 bg-white text-[var(--ink-1)] hover:border-blue-300 hover:bg-blue-50/50 hover:scale-[1.03] active:scale-[0.97]'
                        }`}
                      >
                        {role}
                      </button>
                    )
                  })}
                </div>
                <div className="flex items-center gap-3 my-4">
                  <div className="flex-1 h-px bg-[var(--line)]/60"></div>
                  <span className="text-[12px] text-[var(--ink-3)]">或</span>
                  <div className="flex-1 h-px bg-[var(--line)]/60"></div>
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
                className="w-full rounded-lg border border-[var(--line)]/60 bg-white/50 text-[var(--ink-1)] focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300/60 transition-all px-4 py-2.5 text-[14px]"
              />
              {/* Typing placeholder overlay */}
              {!targetRole && (
                <div className="absolute inset-0 flex items-center pointer-events-none">
                  <span className="text-[var(--ink-3)] px-4 text-[14px]">
                    {typingPlaceholder.text}
                    <span className="inline-block w-px h-[1.1em] bg-[var(--line)] ml-0.5 animate-pulse align-middle" />
                  </span>
                </div>
              )}
            </div>

            {/* Direction quick select */}
            <div className="mt-4">
              <p className="text-[13px] text-[var(--ink-2)] mb-3">选择面试方向</p>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                {[
                  { label: 'C++系统', value: 'C++系统开发', Icon: Cpu },
                  { label: '前端开发', value: '前端开发', Icon: Monitor },
                  { label: 'Java后端', value: 'Java后端开发', Icon: Server },
                  { label: '算法', value: '算法工程师', Icon: Calculator },
                  { label: '产品经理', value: '产品经理', Icon: BarChart3 },
                  { label: '测试开发', value: '测试开发', Icon: ShieldCheck },
                ].map((item) => {
                  const active = targetRole === item.value
                  const Icon = item.Icon
                  return (
                    <motion.button
                      key={item.value}
                      onClick={() => setTargetRole(item.value)}
                      whileHover={{ y: -2 }}
                      whileTap={{ scale: 0.97 }}
                      className={`flex flex-col items-center gap-2 px-2 py-4 rounded-xl border transition-colors duration-200 cursor-pointer ${
                        active
                          ? 'border-blue-400 bg-blue-50 text-blue-700 shadow-sm'
                          : 'border-[var(--line)]/60 bg-white/50 text-[var(--ink-2)] hover:border-blue-300 hover:bg-blue-50/30 hover:text-[var(--ink-1)]'
                      }`}
                    >
                      <div className={`w-9 h-9 rounded-lg flex items-center justify-center transition-colors ${
                        active ? 'bg-blue-100' : 'bg-[var(--bg-card)]'
                      }`}>
                        <Icon className={`w-[18px] h-[18px] ${active ? 'text-blue-600' : 'text-[var(--ink-3)]'}`} />
                      </div>
                      <span className="text-[12px] font-medium">{item.label}</span>
                    </motion.button>
                  )
                })}
              </div>
            </div>

            {/* Question count & type distribution */}
            <div className="mt-5 flex flex-col sm:flex-row gap-4">
              <div className="flex-1">
                <p className="text-[13px] text-[var(--ink-2)] mb-2">题目数量</p>
                <div className="flex gap-2">
                  {[3, 5, 10].map((n) => (
                    <button
                      key={n}
                      onClick={() => {
                        setQuestionCount(n)
                        // Auto adjust type distribution
                        if (n === 3) setTypeDistribution({ technical: 2, scenario: 1, behavioral: 0 })
                        else if (n === 5) setTypeDistribution({ technical: 3, scenario: 1, behavioral: 1 })
                        else if (n === 10) setTypeDistribution({ technical: 6, scenario: 2, behavioral: 2 })
                      }}
                      className={`flex-1 py-2 rounded-lg text-[13px] font-medium border transition-all cursor-pointer ${
                        questionCount === n
                          ? 'border-blue-400 bg-blue-50 text-blue-700'
                          : 'border-[var(--line)]/60 bg-white/50 text-[var(--ink-2)] hover:border-blue-300 hover:bg-blue-50/30'
                      }`}
                    >
                      {n} 题
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex-1">
                <p className="text-[13px] text-[var(--ink-2)] mb-2">题型占比</p>
                <div className="flex items-center gap-1.5">
                  {[
                    { key: 'technical', label: '技术', color: 'bg-blue-100 text-blue-700' },
                    { key: 'scenario', label: '场景', color: 'bg-amber-100 text-amber-700' },
                    { key: 'behavioral', label: '行为', color: 'bg-purple-100 text-purple-700' },
                  ].map((item) => {
                    const count = typeDistribution[item.key] || 0
                    return (
                      <div key={item.key} className="flex-1 flex flex-col items-center gap-1">
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => {
                              const next = { ...typeDistribution }
                              if (count > 0) next[item.key] = count - 1
                              setTypeDistribution(next)
                            }}
                            className="w-6 h-6 rounded-md bg-[var(--bg-card)] text-[var(--ink-2)] text-[12px] font-bold hover:bg-[var(--line)] transition-colors cursor-pointer flex items-center justify-center"
                            disabled={count <= 0}
                          >
                            -
                          </button>
                          <span className={`text-[13px] font-bold w-6 text-center ${count > 0 ? 'text-[var(--ink-1)]' : 'text-[var(--ink-3)]'}`}>
                            {count}
                          </span>
                          <button
                            onClick={() => {
                              const total = Object.values(typeDistribution).reduce((a, b) => a + b, 0)
                              if (total >= questionCount) return
                              const next = { ...typeDistribution }
                              next[item.key] = count + 1
                              setTypeDistribution(next)
                            }}
                            className="w-6 h-6 rounded-md bg-[var(--bg-card)] text-[var(--ink-2)] text-[12px] font-bold hover:bg-[var(--line)] transition-colors cursor-pointer flex items-center justify-center"
                            disabled={Object.values(typeDistribution).reduce((a, b) => a + b, 0) >= questionCount}
                          >
                            +
                          </button>
                        </div>
                        <span className={`text-[11px] px-2 py-0.5 rounded-full ${item.color}`}>{item.label}</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>

            <div className="mt-2 flex items-center justify-between gap-3">
              <p className={`text-[12px] ${shouldAutoBalanceDistribution ? 'text-amber-600' : 'text-emerald-600'}`}>
                {shouldAutoBalanceDistribution
                  ? `当前已分配 ${assignedCount}/${questionCount} 题，开始前会自动补齐为 ${normalizedTypeDistribution.technical} 道技术题`
                  : `题型分配已完成：${assignedCount}/${questionCount} 题`}
              </p>
              {shouldAutoBalanceDistribution && (
                <button
                  onClick={() => setTypeDistribution(normalizedTypeDistribution)}
                  className="text-[12px] text-blue-600 hover:text-blue-700 transition-colors cursor-pointer whitespace-nowrap"
                >
                  一键补齐
                </button>
              )}
            </div>

            <div className="mt-4">
              {!showJd ? (
                <button
                  onClick={() => setShowJd(true)}
                  className="flex items-center gap-1 text-[13px] text-[var(--ink-3)] hover:text-[var(--ink-2)] transition-colors cursor-pointer"
                >
                  <ChevronRight className="w-3.5 h-3.5" />
                  附加 JD（可选，让题目更有针对性）
                </button>
              ) : (
                <div>
                  <button
                    onClick={() => setShowJd(false)}
                    className="flex items-center gap-1 text-[13px] text-[var(--ink-3)] hover:text-[var(--ink-2)] transition-colors cursor-pointer mb-2"
                  >
                    <ChevronDown className="w-3.5 h-3.5" />
                    附加 JD（可选）
                  </button>
                  <textarea
                    value={jdText}
                    onChange={(e) => setJdText(e.target.value)}
                    placeholder="粘贴目标岗位的招聘要求，AI 会据此调整题目方向..."
                    rows={3}
                    className="w-full px-4 py-3 rounded-lg border border-[var(--line)]/60 bg-white/50 text-[14px] text-[var(--ink-1)] placeholder:text-[var(--ink-3)] focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-300/60 transition-all resize-none"
                  />
                </div>
              )}
            </div>

            <div className="flex justify-end mt-5">
              <button
                onClick={() => {
                  const nextDistribution = normalizeTypeDistribution(questionCount, typeDistribution)
                  if (shouldAutoBalanceDistribution) {
                    setTypeDistribution(nextDistribution)
                  }
                  startMutation.mutate({
                    target_role: targetRole.trim(),
                    jd_text: jdText,
                    question_count: questionCount,
                    type_distribution: nextDistribution,
                  })
                }}
                disabled={!targetRole.trim() || startMutation.isPending}
                className={`relative overflow-hidden rounded-lg text-white font-bold transition-all duration-300 cursor-pointer px-6 py-2.5 text-[14px] ${
                  startMutation.isPending
                    ? 'bg-blue-700 cursor-wait'
                    : 'bg-blue-600 hover:bg-blue-700 hover:-translate-y-0.5 hover:shadow-md active:translate-y-0 active:shadow-none active:scale-[0.98]'
                } disabled:opacity-30 disabled:hover:translate-y-0 disabled:hover:shadow-none disabled:cursor-not-allowed`}
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
                    ? loadingStep
                    : `开始面试 · ${questionCount}题 · 约${questionCount * 3}分钟`}
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
              <h2 className="text-[15px] font-semibold text-[var(--ink-1)] mb-4">练习记录</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {displayHistory.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => handleLoadHistory(item.id)}
                    className="relative group text-left rounded-lg border border-[var(--line)]/60 bg-white/50 p-4 hover:bg-white/70 hover:border-slate-300/60 hover:-translate-y-0.5 hover:shadow-sm transition-all duration-200 cursor-pointer"
                  >
                    <button
                      onClick={(e) => handleDelete(item.id, e)}
                      className="absolute top-2 right-2 p-1.5 rounded-md text-[var(--ink-3)] opacity-0 group-hover:opacity-100 hover:text-red-500 hover:bg-red-50 transition-all cursor-pointer"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                    <p className="text-[14px] font-semibold text-[var(--ink-1)] truncate pr-6">
                      {item.target_role}
                    </p>
                    <p className="text-[12px] text-[var(--ink-3)] mt-0.5">
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
                    className="text-[13px] text-[var(--ink-2)] hover:text-[var(--ink-1)] transition-colors cursor-pointer"
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
    const tc = typeColors[q.type] || { bg: 'bg-[var(--bg-card)]', text: 'text-[var(--ink-2)]' }
    const pct = ((currentIndex + 1) / questions.length) * 100
    const isLast = currentIndex === questions.length - 1

    return (
      <div className="flex flex-col h-full w-full">

        {/* ── 顶部栏 ── */}
        <div className="shrink-0 bg-white/70 backdrop-blur-md border-b border-white/30 z-10">
          {/* 进度条 */}
          <div className="w-full h-[2px] bg-[var(--bg-card)]">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${pct}%` }}
              transition={{ duration: 0.4, ease }}
              className="h-full bg-gradient-to-r from-[var(--blue)] to-blue-400"
            />
          </div>
          {/* 导航行 */}
          <div className="px-5 h-12 flex items-center justify-between">
            <button
              onClick={handleRestart}
              className="flex items-center gap-1 text-[13px] text-[var(--ink-3)] hover:text-[var(--ink-1)] transition-colors cursor-pointer"
            >
              <ChevronLeft className="w-4 h-4" />
              返回
            </button>

            {/* 点状进度指示器 */}
            <div className="flex items-center gap-1.5">
              {questions.map((_, i) => (
                <div
                  key={i}
                  className={`rounded-full transition-all duration-300 ${
                    i < currentIndex
                      ? 'w-1.5 h-1.5 bg-blue-400'
                      : i === currentIndex
                      ? 'w-2 h-2 bg-[var(--blue)] ring-2 ring-blue-200'
                      : 'w-1.5 h-1.5 bg-[var(--line)]'
                  }`}
                />
              ))}
            </div>

            <span className={`text-[11px] font-medium px-2.5 py-1 rounded-full ${tc.bg} ${tc.text}`}>
              {typeLabel(q.type)}
            </span>
          </div>
        </div>

        {/* ── 对话流区域 ── */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-[680px] mx-auto px-4 py-6">
            <AnimatePresence mode="wait">
              <motion.div
                key={currentIndex}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.25, ease }}
                className="flex flex-col gap-5"
              >
                {/* 面试官气泡：主题目 */}
                <InterviewerBubble>
                  <p className="text-[15px] font-medium text-[var(--ink-1)] leading-[1.8]">
                    {q.question}
                  </p>
                  <div className="mt-2.5 flex items-center gap-2 flex-wrap">
                    <span className="text-[11px] text-[var(--ink-3)]">考察</span>
                    <span className="text-[12px] text-[var(--ink-2)]">{q.focus_area}</span>
                    <span className="text-[11px] text-[var(--ink-3)]">·</span>
                    <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${
                      q.difficulty === 'easy'
                        ? 'bg-emerald-50 text-emerald-600'
                        : q.difficulty === 'medium'
                        ? 'bg-amber-50 text-amber-600'
                        : 'bg-red-50 text-red-500'
                    }`}>
                      {q.difficulty === 'easy' ? '基础' : q.difficulty === 'medium' ? '进阶' : '专家'}
                    </span>
                  </div>
                </InterviewerBubble>

                {/* 用户主回答气泡 */}
                <UserAnswerBubble
                  value={currentAnswer}
                  onChange={setCurrentAnswer}
                  onBlur={handleMainAnswerBlur}
                  placeholder="在这里写下你的回答..."
                  minHint={30}
                />

                {/* 追问对话流 */}
                {currentFollowUps.map((turn, idx) => (
                  <motion.div
                    key={`followup-${idx}`}
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3, ease }}
                    className="flex flex-col gap-5"
                  >
                    {/* 面试官追问气泡 */}
                    <InterviewerBubble isFollowUp>
                      <div className="flex items-center gap-1.5 mb-1.5">
                        <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">
                          追问 {idx + 1}
                        </span>
                      </div>
                      <p className="text-[14px] font-medium text-[var(--ink-1)] leading-[1.8]">
                        {turn.question}
                      </p>
                    </InterviewerBubble>

                    {/* 用户追问回答气泡 */}
                    <UserAnswerBubble
                      value={turn.answer}
                      onChange={(val) => {
                        const next = currentFollowUps.map((item, turnIndex) =>
                          turnIndex === idx ? { ...item, answer: val } : item
                        )
                        setCurrentFollowUps(next)
                      }}
                      onBlur={() => {
                        if (idx === currentFollowUps.length - 1 && turn.answer.trim().length >= 10) {
                          handleMainAnswerBlur()
                        }
                      }}
                      placeholder="补充这轮追问的回答..."
                      isFollowUp
                      minHint={10}
                    />
                  </motion.div>
                ))}

                {/* AI 思考中气泡 */}
                {followUpMutation.isPending && <ThinkingBubble />}

                {/* 追问完毕提示 */}
                {followUpInfo && !followUpMutation.isPending && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex justify-center"
                  >
                    <span className="text-[12px] text-[var(--ink-3)] bg-white/70 backdrop-blur-sm px-3 py-1.5 rounded-full border border-white/40">
                      {followUpInfo}
                    </span>
                  </motion.div>
                )}

                {/* 追问错误提示 */}
                {followUpError && (
                  <p className="text-[12px] text-red-500 text-center">{followUpError}</p>
                )}

              </motion.div>
            </AnimatePresence>
          </div>
        </div>

        {/* ── 底部操作栏 ── */}
        <div className="shrink-0 bg-white/70 backdrop-blur-md border-t border-white/30 px-5 h-16 flex items-center justify-between gap-4 z-10">
          {/* 语音输入 */}
          {isSupported && (
            <button
              onClick={isListening ? stop : start}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-[13px] font-medium transition-all cursor-pointer ${
                isListening
                  ? 'bg-red-50 text-red-600 border border-red-200'
                  : 'text-[var(--ink-3)] hover:text-[var(--ink-2)] hover:bg-[var(--bg-card)]/60 border border-transparent'
              }`}
            >
              <Mic className={`w-4 h-4 ${isListening ? 'animate-pulse' : ''}`} />
              {isListening ? '停止录音' : '语音输入'}
            </button>
          )}
          {!isSupported && <div />}

          {/* 导航按钮 */}
          <div className="flex items-center gap-3">
            <button
              onClick={handlePrev}
              disabled={currentIndex === 0}
              className="flex items-center gap-1 px-3 py-2 text-[13px] font-medium text-[var(--ink-3)] hover:text-[var(--ink-1)] transition-colors disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
            >
              <ChevronLeft className="w-4 h-4" />
              上一题
            </button>

            {isLast ? (
              <button
                onClick={handleSubmit}
                disabled={submitMutation.isPending}
                className="flex items-center gap-2 px-5 py-2 rounded-xl bg-[var(--blue)] text-white text-[13px] font-semibold hover:bg-[var(--blue-deep)] active:scale-[0.98] transition-all cursor-pointer shadow-sm shadow-blue-500/20 disabled:opacity-60 disabled:cursor-wait"
              >
                提交全部答案
                <CheckCircle2 className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={handleNext}
                className="flex items-center gap-2 px-5 py-2 rounded-xl bg-[var(--blue)] text-white text-[13px] font-semibold hover:bg-[var(--blue-deep)] active:scale-[0.98] transition-all cursor-pointer shadow-sm shadow-blue-500/20"
              >
                下一题
                <ChevronRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* 提交错误提示 */}
        {submitError && (
          <div className="shrink-0 px-5 pb-3 text-center">
            <p className="text-[12px] text-red-500">{submitError}</p>
          </div>
        )}
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
          <h2 className="text-[18px] font-bold text-[var(--ink-1)] mb-8">正在评估...</h2>

          <div className="space-y-4">
            <div className="flex items-center gap-3">
              {fakeStep >= 1 ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
              ) : (
                <Loader2 className="w-5 h-5 animate-spin text-blue-500 shrink-0" />
              )}
              <span className={fakeStep >= 1 ? 'text-[13px] text-[var(--ink-2)]' : 'text-[13px] text-[var(--ink-1)] font-semibold'}>
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
                fakeStep >= 2 ? 'text-[13px] text-[var(--ink-2)]' :
                fakeStep >= 1 ? 'text-[13px] text-[var(--ink-1)] font-semibold' :
                'text-[13px] text-[var(--ink-3)]'
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
              <span className={fakeStep >= 2 ? 'text-[13px] text-[var(--ink-1)] font-semibold' : 'text-[13px] text-[var(--ink-3)]'}>
                综合评分与建议生成
              </span>
              {fakeStep >= 2 && <span className="text-[12px] text-blue-500 ml-auto">进行中...</span>}
            </div>
          </div>

          <p className="text-[12px] text-[var(--ink-3)] mt-8">通常 15-30 秒</p>
        </motion.div>
      </div>
    )
  }

  /* ── Phase: Results ── */
  if (phase === 'results' && evaluation) {
    const answeredFollowUpCount = countAnsweredFollowUps(answers)

    return (
      <div className="flex flex-col h-full w-full overflow-y-auto pb-12">
        <div className="max-w-[720px] mx-auto px-6 py-8 w-full">
          {/* Back button */}
          <motion.button
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
            onClick={handleRestart}
            className="flex items-center gap-1.5 text-[13px] text-[var(--ink-3)] hover:text-[var(--ink-2)] transition-colors cursor-pointer mb-6"
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
                  <p className="text-[15px] text-[var(--ink-2)] leading-relaxed max-w-[420px]">
                    {evaluation.overall_comment}
                  </p>
                </div>
              </motion.div>
            )
          })()}

          {answeredFollowUpCount > 0 && (
            <div className="mb-8 rounded-xl border border-blue-100/70 bg-blue-50/60 px-5 py-4">
              <p className="text-[13px] font-semibold text-blue-800">本场共完成 {answeredFollowUpCount} 轮 AI 追问</p>
              <p className="mt-1 text-[12px] text-blue-700/80 leading-relaxed">
                评分已把你在深挖问题中的补充细节、稳定性和自洽程度一起算进去。
              </p>
            </div>
          )}

          {/* Per-question evaluations */}
          <div className="mb-8">
            <h3 className="text-[14px] font-semibold text-[var(--ink-1)] mb-4">
              逐题评分
            </h3>
            <div className="space-y-3">
              {(evaluation.per_question || []).map((pq, idx) => (
                <QuestionEvalRow
                  key={pq.question_id}
                  eval={pq}
                  question={questions[idx] || { id: pq.question_id, type: 'technical', question: '', focus_area: '', difficulty: '' }}
                  answer={answers[idx] || { question_id: pq.question_id, answer: '', follow_ups: [] }}
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
                  <h3 className="text-[13px] font-bold text-[var(--ink-3)] uppercase tracking-wider mb-3">
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
                  <h3 className="text-[13px] font-bold text-[var(--ink-3)] uppercase tracking-wider mb-3">
                    改进建议
                  </h3>
                  <ul className="space-y-2">
                    {evaluation.tips.map((tip, i) => (
                      <li key={i} className="text-[13px] text-[var(--ink-2)] leading-relaxed">
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
              className="text-[14px] text-[var(--ink-3)] hover:text-[var(--ink-2)] transition-colors cursor-pointer"
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
        <span className="text-[11px] text-[var(--ink-3)] mt-1">综合得分</span>
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
  answer: Answer
  index: number
}) {
  const [showSuggested, setShowSuggested] = useState(false)
  const [showMyAnswer, setShowMyAnswer] = useState(false)
  const tc = typeColors[question.type] || { bg: 'bg-[var(--bg-card)]', text: 'text-[var(--ink-2)]' }
  const answeredFollowUps = (answer.follow_ups || []).filter((item) => item.question)

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
      className="rounded-xl border border-[var(--line)]/60 bg-white/50 overflow-hidden hover:border-slate-300/60 hover:bg-white/70 hover:shadow-sm transition-all duration-200"
    >
      {/* 顶部分数色条 */}
      <div className="h-1 bg-[var(--bg-card)]">
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
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <span className="text-[12px] font-bold text-[var(--ink-3)] tabular-nums">
                {String(index + 1).padStart(2, '0')}
              </span>
              <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${tc.bg} ${tc.text}`}>
                {typeLabel(question.type)}
              </span>
              <span className="text-[11px] text-[var(--ink-3)]">
                {question.focus_area}
              </span>
              {answeredFollowUps.length > 0 && (
                <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-100">
                  追问 {answeredFollowUps.length} 轮
                </span>
              )}
            </div>
            <p className="text-[13px] text-[var(--ink-2)] leading-relaxed line-clamp-2">
              {question.question}
            </p>
          </div>
          <span className={`text-[28px] font-black tabular-nums shrink-0 leading-none ${scoreColor(ev.score)}`}>
            <CountUp value={ev.score} delay={700 + index * 150} />
          </span>
        </div>

        {/* Strengths & Improvements */}
        {(ev.strengths.length > 0 || ev.improvements.length > 0) && (
          <div className="mt-4 pt-4 border-t border-[var(--line)]">
            {ev.strengths.length > 0 && (
              <div className="space-y-1.5 mb-2">
                {ev.strengths.map((s, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <span className="text-emerald-500 text-[12px] mt-0.5 shrink-0">✓</span>
                    <p className="text-[13px] text-[var(--ink-2)] leading-relaxed">{s}</p>
                  </div>
                ))}
              </div>
            )}
            {ev.improvements.length > 0 && (
              <div className="space-y-1.5">
                {ev.improvements.map((s, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <span className="text-amber-500 text-[12px] mt-0.5 shrink-0">△</span>
                    <p className="text-[13px] text-[var(--ink-2)] leading-relaxed">{s}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {ev.follow_up_comment && (
          <div className="mt-4 rounded-lg border border-blue-100/70 bg-blue-50/60 px-4 py-3">
            <p className="text-[12px] font-semibold text-blue-800">追问表现</p>
            <p className="mt-1 text-[13px] text-blue-900/80 leading-relaxed">{ev.follow_up_comment}</p>
          </div>
        )}

        {/* My answer toggle */}
        {(answer.answer || answeredFollowUps.length > 0) && (
          <>
            <button
              onClick={() => setShowMyAnswer((v) => !v)}
              className="mt-4 flex items-center gap-1 text-[12px] font-semibold text-[var(--ink-3)] hover:text-[var(--ink-2)] transition-colors cursor-pointer"
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
                  <div className="mt-2 space-y-3">
                    {answer.answer && (
                      <div className="p-4 rounded-lg bg-blue-50/50 border border-blue-100/60 text-[13px] text-[var(--ink-2)] leading-[1.8] whitespace-pre-wrap">
                        {answer.answer}
                      </div>
                    )}
                    {answeredFollowUps.map((turn, idx) => (
                      <div key={`${turn.question}-${idx}`} className="rounded-lg border border-[var(--line)]/70 bg-[var(--bg-card)]/70 p-4">
                        <p className="text-[12px] font-semibold text-[var(--ink-2)]">追问 {idx + 1}</p>
                        <p className="mt-1 text-[13px] text-[var(--ink-1)] leading-relaxed">{turn.question}</p>
                        <p className="mt-2 text-[13px] text-[var(--ink-2)] leading-[1.8] whitespace-pre-wrap">
                          {turn.answer || '（未作答）'}
                        </p>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </>
        )}

        {/* Suggested answer toggle */}
        <button
          onClick={() => setShowSuggested((v) => !v)}
          className="mt-4 flex items-center gap-1 text-[12px] font-semibold text-[var(--ink-3)] hover:text-[var(--ink-2)] transition-colors cursor-pointer"
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
              <div className="mt-2 p-4 rounded-lg bg-[var(--bg-card)]/80 text-[13px] text-[var(--ink-2)] leading-[1.8]">
                {ev.suggested_answer}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}

/* ── Sub-component: InterviewerBubble ── */

function InterviewerBubble({
  children,
  isFollowUp = false,
}: {
  children: ReactNode
  isFollowUp?: boolean
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: 'spring', stiffness: 350, damping: 26 }}
      className="flex items-start gap-3"
    >
      <motion.div
        initial={{ scale: 0.8 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 400, damping: 20, delay: 0.05 }}
        className={`shrink-0 w-9 h-9 rounded-full flex items-center justify-center shadow-md ${
          isFollowUp ? 'bg-amber-700' : 'bg-slate-800'
        }`}
      >
        <Bot className="w-[18px] h-[18px] text-white" />
      </motion.div>
      <div className={`flex-1 rounded-2xl rounded-tl-sm px-4 py-3.5 shadow-sm border-[1.5px] backdrop-blur-sm transition-all duration-200 ${
        isFollowUp
          ? 'bg-white/70 border-amber-300/60 hover:border-amber-400/80 hover:shadow-md'
          : 'bg-white/70 border-[var(--line)]/60 hover:border-slate-300/80 hover:shadow-md'
      }`}>
        {children}
      </div>
    </motion.div>
  )
}

/* ── Sub-component: UserAnswerBubble ── */

function UserAnswerBubble({
  value,
  onChange,
  onBlur,
  placeholder,
  isFollowUp = false,
  minHint = 30,
}: {
  value: string
  onChange: (val: string) => void
  onBlur?: () => void
  placeholder: string
  isFollowUp?: boolean
  minHint?: number
}) {
  const len = value.length
  const lenColor =
    len === 0 ? 'text-[var(--ink-3)]'
    : len < minHint ? 'text-amber-500'
    : len <= 300 ? 'text-emerald-500'
    : 'text-[var(--ink-3)]'

  const taRef = useRef<HTMLTextAreaElement>(null)
  useEffect(() => {
    const ta = taRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = `${ta.scrollHeight}px`
  }, [value])

  const [isFocused, setIsFocused] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, y: 8, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: 'spring', stiffness: 350, damping: 26 }}
      className="flex items-start gap-3 flex-row-reverse"
    >
      <motion.div
        initial={{ scale: 0.8 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 400, damping: 20, delay: 0.05 }}
        className={`shrink-0 w-9 h-9 rounded-full flex items-center justify-center shadow-md text-white text-[12px] font-bold ${
          isFollowUp ? 'bg-[var(--bg-card)]0' : 'bg-[var(--blue)]'
        }`}
      >
        你
      </motion.div>
      <div
        className={`flex-1 rounded-2xl rounded-tr-sm shadow-sm border-[1.5px] overflow-hidden backdrop-blur-sm transition-all duration-200 ${
          isFollowUp
            ? isFocused
              ? 'bg-[var(--bg-card)]/80 border-slate-400/70 ring-2 ring-slate-400/15 shadow-md'
              : 'bg-[var(--bg-card)]/60 border-slate-300/60 hover:border-slate-400/80'
            : isFocused
              ? 'bg-blue-50/80 border-blue-400/70 ring-2 ring-blue-400/20 shadow-md'
              : 'bg-blue-50/60 border-blue-300/60 hover:border-blue-400/80'
        }`}
      >
        <textarea
          ref={taRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => { setIsFocused(false); onBlur?.() }}
          placeholder={placeholder}
          rows={isFollowUp ? 2 : 4}
          className="w-full px-4 py-3.5 bg-transparent text-[14px] text-[var(--ink-1)] placeholder:text-[var(--ink-3)] focus:outline-none resize-none leading-[1.8]"
          style={{ minHeight: isFollowUp ? '72px' : '120px', maxHeight: '320px' }}
        />
        <div className="px-4 pb-2.5 flex justify-end">
          <span className={`text-[11px] tabular-nums transition-colors ${lenColor}`}>
            {len} 字{len < minHint && len > 0 ? `（建议至少 ${minHint} 字）` : ''}
          </span>
        </div>
      </div>
    </motion.div>
  )
}

/* ── Sub-component: ThinkingBubble ── */

function ThinkingBubble() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 350, damping: 26 }}
      className="flex items-start gap-3"
    >
      <motion.div
        animate={{ scale: [1, 1.05, 1] }}
        transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        className="shrink-0 w-9 h-9 rounded-full bg-slate-800 flex items-center justify-center shadow-md"
      >
        <Bot className="w-[18px] h-[18px] text-white" />
      </motion.div>
      <div className="bg-white/70 backdrop-blur-sm border-[1.5px] border-[var(--line)]/60 rounded-2xl rounded-tl-sm px-5 py-4 shadow-sm">
        <div className="flex items-center gap-2">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="w-2 h-2 rounded-full bg-blue-400"
              animate={{ y: [0, -6, 0], opacity: [0.5, 1, 0.5] }}
              transition={{
                duration: 0.9,
                repeat: Infinity,
                delay: i * 0.18,
                ease: 'easeInOut',
              }}
            />
          ))}
        </div>
      </div>
    </motion.div>
  )
}
