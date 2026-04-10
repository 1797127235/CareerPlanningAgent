import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ClipboardCheck, ChevronRight, Loader2, X } from 'lucide-react'
import { generateSjt, submitSjt } from '@/api/profiles'
import type { SjtQuestion, SjtAnswer, SjtDimensionResult } from '@/api/profiles'

const LEVEL_STYLE: Record<string, { bg: string; text: string }> = {
  '待发展': { bg: 'bg-slate-100', text: 'text-slate-600' },
  '基础': { bg: 'bg-blue-100', text: 'text-blue-700' },
  '良好': { bg: 'bg-emerald-100', text: 'text-emerald-700' },
  '优秀': { bg: 'bg-amber-100', text: 'text-amber-700' },
}

const DIM_LABEL: Record<string, string> = {
  communication: '沟通能力',
  learning: '学习能力',
  collaboration: '协作能力',
  innovation: '创新能力',
  resilience: '抗压能力',
}

type Phase = 'cta' | 'generating' | 'answering' | 'submitting' | 'done'

interface Props {
  onComplete: () => void
}

export default function SjtCtaCard({ onComplete }: Props) {
  const [phase, setPhase] = useState<Phase>('cta')
  const [sessionId, setSessionId] = useState('')
  const [questions, setQuestions] = useState<SjtQuestion[]>([])
  const [currentIdx, setCurrentIdx] = useState(0)
  const [answers, setAnswers] = useState<SjtAnswer[]>([])
  const [bestId, setBestId] = useState<string | null>(null)
  const [worstId, setWorstId] = useState<string | null>(null)
  const [results, setResults] = useState<SjtDimensionResult[]>([])
  const [overallLevel, setOverallLevel] = useState('')
  const [error, setError] = useState('')

  const handleStart = useCallback(async () => {
    setError('')
    setPhase('generating')
    try {
      const data = await generateSjt()
      setSessionId(data.session_id)
      setQuestions(data.questions)
      setCurrentIdx(0)
      setAnswers([])
      setPhase('answering')
    } catch (e) {
      setError(e instanceof Error ? e.message : '生成失败，请重试')
      setPhase('cta')
    }
  }, [])

  const handleNext = useCallback(() => {
    if (!bestId || !worstId) return
    const q = questions[currentIdx]
    const newAnswers = [...answers, { question_id: q.id, best: bestId, worst: worstId }]
    setAnswers(newAnswers)
    setBestId(null)
    setWorstId(null)

    if (currentIdx + 1 < questions.length) {
      setCurrentIdx(currentIdx + 1)
    } else {
      // Submit
      setPhase('submitting')
      submitSjt(sessionId, newAnswers)
        .then((res) => {
          setResults(res.dimensions)
          setOverallLevel(res.overall_level)
          setPhase('done')
        })
        .catch((e) => {
          setError(e instanceof Error ? e.message : '提交失败，请重试')
          setPhase('answering')
        })
    }
  }, [bestId, worstId, questions, currentIdx, answers, sessionId])

  const handleOptionClick = (optionId: string, role: 'best' | 'worst') => {
    if (role === 'best') {
      setBestId(optionId === bestId ? null : optionId)
      if (optionId === worstId) setWorstId(null)
    } else {
      setWorstId(optionId === worstId ? null : optionId)
      if (optionId === bestId) setBestId(null)
    }
  }

  // ── Phase: CTA ──
  if (phase === 'cta') {
    return (
      <div className="glass p-6 text-center">
        <div className="w-12 h-12 rounded-xl bg-blue-50 flex items-center justify-center mx-auto mb-4">
          <ClipboardCheck className="w-6 h-6 text-[var(--blue)]" />
        </div>
        <h3 className="text-[16px] font-bold text-slate-800 mb-1">完成情境评估，了解你的软技能画像</h3>
        <p className="text-[13px] text-slate-500 mb-5">15 道基于你经历的情境题，约 5-8 分钟</p>
        {error && <p className="text-[13px] text-red-500 mb-3">{error}</p>}
        <button
          onClick={handleStart}
          className="btn-cta px-6 py-2.5 text-[14px] font-semibold cursor-pointer"
        >
          开始评估
        </button>
      </div>
    )
  }

  // ── Phase: Generating ──
  if (phase === 'generating') {
    return (
      <div className="glass p-6 flex items-center gap-4">
        <Loader2 className="w-6 h-6 text-[var(--blue)] animate-spin shrink-0" />
        <div>
          <p className="text-[14px] font-medium text-slate-700">正在根据你的经历生成个性化情境题...</p>
          <p className="text-[12px] text-slate-400 mt-0.5">这可能需要几秒钟</p>
        </div>
      </div>
    )
  }

  // ── Phase: Answering ──
  if (phase === 'answering') {
    const q = questions[currentIdx]
    return (
      <div className="glass p-6">
        <div className="flex items-center justify-between mb-4">
          <span className="text-[12px] font-semibold text-slate-400 uppercase tracking-wider">
            {DIM_LABEL[q.dimension] || q.dimension}
          </span>
          <span className="text-[12px] font-mono text-slate-400">
            {currentIdx + 1} / {questions.length}
          </span>
        </div>

        {/* Progress bar */}
        <div className="w-full h-1 bg-slate-100 rounded-full mb-5">
          <motion.div
            className="h-full bg-[var(--blue)] rounded-full"
            initial={false}
            animate={{ width: `${((currentIdx + 1) / questions.length) * 100}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>

        <p className="text-[14px] text-slate-700 leading-relaxed mb-5">{q.scenario}</p>

        {error && <p className="text-[13px] text-red-500 mb-3">{error}</p>}

        <div className="space-y-2.5 mb-5">
          {q.options.map((o) => {
            const isBest = bestId === o.id
            const isWorst = worstId === o.id
            return (
              <div
                key={o.id}
                className={`rounded-xl border p-3 transition-all ${
                  isBest
                    ? 'border-emerald-300 bg-emerald-50'
                    : isWorst
                    ? 'border-red-300 bg-red-50'
                    : 'border-slate-200 bg-white/50'
                }`}
              >
                <p className="text-[13px] text-slate-700 mb-2">{o.text}</p>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleOptionClick(o.id, 'best')}
                    className={`text-[11px] px-2.5 py-1 rounded-lg font-medium transition-all cursor-pointer ${
                      isBest
                        ? 'bg-emerald-500 text-white'
                        : 'bg-slate-100 text-slate-500 hover:bg-emerald-100 hover:text-emerald-700'
                    }`}
                  >
                    最佳
                  </button>
                  <button
                    onClick={() => handleOptionClick(o.id, 'worst')}
                    className={`text-[11px] px-2.5 py-1 rounded-lg font-medium transition-all cursor-pointer ${
                      isWorst
                        ? 'bg-red-500 text-white'
                        : 'bg-slate-100 text-slate-500 hover:bg-red-100 hover:text-red-700'
                    }`}
                  >
                    最差
                  </button>
                </div>
              </div>
            )
          })}
        </div>

        <button
          onClick={handleNext}
          disabled={!bestId || !worstId}
          className="btn-cta w-full py-2.5 text-[14px] font-semibold cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-1.5"
        >
          {currentIdx + 1 < questions.length ? '下一题' : '提交评估'}
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    )
  }

  // ── Phase: Submitting ──
  if (phase === 'submitting') {
    return (
      <div className="glass p-6 flex items-center gap-4">
        <Loader2 className="w-6 h-6 text-[var(--blue)] animate-spin shrink-0" />
        <div>
          <p className="text-[14px] font-medium text-slate-700">正在分析你的作答...</p>
          <p className="text-[12px] text-slate-400 mt-0.5">生成评估结果和改进建议</p>
        </div>
      </div>
    )
  }

  // ── Phase: Done ──
  const overallStyle = LEVEL_STYLE[overallLevel] || LEVEL_STYLE['待发展']
  return (
    <div className="glass p-6">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="text-[16px] font-bold text-slate-800">评估完成</h3>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[13px] text-slate-500">综合等级</span>
            <span className={`text-[12px] font-semibold px-2.5 py-0.5 rounded-lg ${overallStyle.bg} ${overallStyle.text}`}>
              {overallLevel}
            </span>
          </div>
        </div>
        <button
          onClick={onComplete}
          className="p-2 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <AnimatePresence>
        <div className="space-y-3">
          {results.map((dim, i) => {
            const style = LEVEL_STYLE[dim.level] || LEVEL_STYLE['待发展']
            return (
              <motion.div
                key={dim.key}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                className="rounded-xl border border-slate-150 bg-white/60 p-4"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-[14px] font-semibold text-slate-700">
                    {DIM_LABEL[dim.key] || dim.key}
                  </span>
                  <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-lg ${style.bg} ${style.text}`}>
                    {dim.level}
                  </span>
                </div>
                {dim.advice && (
                  <p className="text-[13px] text-slate-500 leading-relaxed">{dim.advice}</p>
                )}
              </motion.div>
            )
          })}
        </div>
      </AnimatePresence>
    </div>
  )
}
