import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Check, ChevronRight, Sparkles } from 'lucide-react'
import { rawFetch } from '@/api/client'

/* ── Types ── */

interface Preferences {
  work_style: string
  value_priority: string
  work_intensity: string
  company_type: string
  ai_attitude: string
  current_stage: string
}

interface Question {
  key: keyof Preferences
  title: string
  options: Array<{ value: string; label: string; desc: string }>
}

/* ── Questions ── */

const QUESTIONS: Question[] = [
  {
    key: 'work_style',
    title: '你更喜欢哪种工作方式？',
    options: [
      { value: 'tech', label: '深挖技术', desc: '沉浸在代码和架构中' },
      { value: 'product', label: '做产品', desc: '和用户需求打交道' },
      { value: 'data', label: '分析数据', desc: '从数据中找规律和洞察' },
      { value: 'management', label: '带团队', desc: '协调资源、推动目标' },
    ],
  },
  {
    key: 'value_priority',
    title: '你更看重什么？',
    options: [
      { value: 'growth', label: '技术成长', desc: '持续学习新技术' },
      { value: 'stability', label: '薪资稳定', desc: '可预期的收入和发展' },
      { value: 'balance', label: '工作生活平衡', desc: '不想被工作填满生活' },
      { value: 'innovation', label: '行业前景', desc: '做有创新空间的事' },
    ],
  },
  {
    key: 'work_intensity',
    title: '你对工作强度的态度？',
    options: [
      { value: 'high', label: '可以拼', desc: '成长期愿意高强度投入' },
      { value: 'moderate', label: '偶尔加班', desc: '忙的时候可以接受' },
      { value: 'low', label: '准时下班', desc: '工作效率比时长重要' },
    ],
  },
  {
    key: 'company_type',
    title: '你更倾向哪类公司？',
    options: [
      { value: 'big_tech', label: '大厂', desc: '字节/腾讯/阿里等' },
      { value: 'growing', label: '成长型公司', desc: '有潜力的中型企业' },
      { value: 'startup', label: '初创团队', desc: '快节奏、多面手' },
      { value: 'state_owned', label: '国企/事业单位', desc: '稳定优先' },
    ],
  },
  {
    key: 'ai_attitude',
    title: '面对 AI 浪潮，你的态度？',
    options: [
      { value: 'do_ai', label: '拥抱 AI', desc: '想做 AI 相关方向' },
      { value: 'avoid_ai', label: '找 AI 替代不了的', desc: '做需要人类判断力的工作' },
      { value: 'no_preference', label: '无所谓', desc: '看机会和薪资决定' },
    ],
  },
  {
    key: 'current_stage',
    title: '你现在最焦虑的是？',
    options: [
      { value: 'lost', label: '不知道选什么方向', desc: '选择太多反而迷茫' },
      { value: 'know_gap', label: '方向有了但技能不够', desc: '知道差距但不知从何补起' },
      { value: 'ready', label: '技能够但找不到机会', desc: '投了简历没什么回音' },
      { value: 'not_started', label: '还没认真想过', desc: '刚开始关注就业' },
    ],
  },
]

const ease = [0.23, 1, 0.32, 1] as const

/* ── Component ── */

interface Props {
  initialPreferences?: Preferences | null
  onSaved?: () => void
}

export function PreferencesCard({ initialPreferences, onSaved }: Props) {
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState<Partial<Preferences>>({})
  const [saving, setSaving] = useState(false)
  const [completed, setCompleted] = useState(false)

  // If preferences already exist, show summary
  const hasExisting = initialPreferences && Object.values(initialPreferences).some(v => v)

  useEffect(() => {
    if (initialPreferences) {
      setAnswers(initialPreferences)
      if (hasExisting) setCompleted(true)
    }
  }, [initialPreferences, hasExisting])

  const currentQ = QUESTIONS[step]
  const totalSteps = QUESTIONS.length
  const progress = Math.round(((step + (answers[currentQ?.key] ? 1 : 0)) / totalSteps) * 100)

  const handleSelect = (value: string) => {
    const newAnswers = { ...answers, [currentQ.key]: value }
    setAnswers(newAnswers)

    // Auto-advance after short delay
    setTimeout(() => {
      if (step < totalSteps - 1) {
        setStep(step + 1)
      } else {
        handleSave(newAnswers)
      }
    }, 300)
  }

  const handleSave = async (data: Partial<Preferences>) => {
    setSaving(true)
    try {
      await rawFetch('/profiles/preferences', {
        method: 'PATCH',
        body: JSON.stringify(data),
      })
      setCompleted(true)
      onSaved?.()
    } catch {
      // Silently fail — preferences are not critical
    } finally {
      setSaving(false)
    }
  }

  // Summary view (after completion)
  if (completed && hasExisting) {
    const summaryItems = QUESTIONS.map(q => {
      const selected = q.options.find(o => o.value === (answers as Record<string, string>)[q.key])
      return selected ? { question: q.title, answer: selected.label } : null
    }).filter(Boolean) as Array<{ question: string; answer: string }>

    return (
      <div className="glass p-5">
        <div className="g-inner">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-[14px] font-bold text-slate-700 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-500" />
              就业意愿
            </h3>
            <button
              onClick={() => { setCompleted(false); setStep(0) }}
              className="text-[12px] text-[var(--blue)] font-medium cursor-pointer hover:underline"
            >
              重新填写
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {summaryItems.map((item, i) => (
              <span
                key={i}
                className="px-3 py-1.5 rounded-lg text-[12px] font-medium text-slate-600 bg-white/50 border border-slate-200/60"
              >
                {item.answer}
              </span>
            ))}
          </div>
        </div>
      </div>
    )
  }

  // Question flow
  return (
    <div className="glass overflow-hidden">
      <div className="g-inner">
        {/* Progress bar */}
        <div className="px-5 pt-5 pb-3">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-[14px] font-bold text-slate-700 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-500" />
              了解你的就业意愿
            </h3>
            <span className="text-[12px] text-slate-400 tabular-nums">{step + 1} / {totalSteps}</span>
          </div>
          <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-blue-400 to-blue-600 rounded-full"
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.4, ease }}
            />
          </div>
        </div>

        {/* Question */}
        <div className="px-5 pb-5">
          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.25, ease }}
            >
              <p className="text-[15px] font-semibold text-slate-800 mb-4">{currentQ.title}</p>
              <div className="grid grid-cols-2 gap-2.5">
                {currentQ.options.map((opt) => {
                  const isSelected = answers[currentQ.key] === opt.value
                  return (
                    <button
                      key={opt.value}
                      onClick={() => handleSelect(opt.value)}
                      disabled={saving}
                      className={`relative flex flex-col items-start p-4 rounded-xl border-2 text-left cursor-pointer transition-all duration-200 group
                        ${isSelected
                          ? 'border-[var(--blue)] bg-blue-50/60 shadow-sm shadow-blue-500/10'
                          : 'border-slate-200/80 bg-white/40 hover:border-blue-200 hover:bg-blue-50/20'
                        }
                      `}
                    >
                      {/* Check indicator */}
                      <div className={`absolute top-3 right-3 w-5 h-5 rounded-full flex items-center justify-center transition-all
                        ${isSelected
                          ? 'bg-[var(--blue)] text-white scale-100'
                          : 'bg-slate-100 text-transparent scale-90'
                        }
                      `}>
                        <Check className="w-3 h-3" />
                      </div>

                      <span className={`text-[14px] font-semibold mb-1 transition-colors
                        ${isSelected ? 'text-[var(--blue)]' : 'text-slate-700 group-hover:text-slate-900'}
                      `}>
                        {opt.label}
                      </span>
                      <span className="text-[12px] text-slate-400 leading-relaxed pr-5">
                        {opt.desc}
                      </span>
                    </button>
                  )
                })}
              </div>
            </motion.div>
          </AnimatePresence>

          {/* Navigation */}
          {step > 0 && (
            <button
              onClick={() => setStep(step - 1)}
              className="mt-3 text-[12px] text-slate-400 hover:text-slate-600 cursor-pointer transition-colors"
            >
              上一题
            </button>
          )}
        </div>

        {/* Saving state */}
        {saving && (
          <div className="px-5 pb-4 flex items-center gap-2 text-[13px] text-[var(--blue)]">
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            保存中...
          </div>
        )}
      </div>
    </div>
  )
}
