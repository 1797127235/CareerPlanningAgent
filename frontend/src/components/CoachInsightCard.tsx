import { Compass, ChevronRight, Lightbulb, MessageSquare } from 'lucide-react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { sendToCoachWithOpen } from '@/hooks/useCoachTrigger'
import type { CoachInsight } from '@/types/jd'

const ease = [0.23, 1, 0.32, 1] as const

interface CoachInsightCardProps {
  insight: CoachInsight
  delay?: number
}

export function CoachInsightCard({ insight, delay = 0.4 }: CoachInsightCardProps) {
  const navigate = useNavigate()

  const handleCta = (action: string, target?: string, prompt?: string) => {
    if (action === 'navigate' && target) {
      navigate(target)
    } else if (action === 'open_chat' && prompt) {
      sendToCoachWithOpen(prompt)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4, ease }}
      className="glass p-5 mb-5 border-l-4 border-l-[var(--blue)]"
    >
      <div className="flex items-center gap-2 mb-3">
        <div className="w-7 h-7 rounded-lg bg-[var(--blue)]/10 flex items-center justify-center">
          <Compass className="w-4 h-4 text-[var(--blue)]" />
        </div>
        <span className="text-[13px] font-bold text-slate-700">智析教练发现</span>
      </div>

      <p className="text-[14px] text-slate-700 leading-relaxed mb-3">
        {insight.insight}
      </p>

      {insight.evidence && insight.evidence.length > 0 && (
        <div className="mb-4 space-y-1.5">
          {insight.evidence.map((item, idx) => (
            <div key={idx} className="flex items-start gap-2">
              <Lightbulb className="w-3.5 h-3.5 text-amber-500 mt-0.5 shrink-0" />
              <span className="text-[12px] text-slate-500 leading-relaxed">{item}</span>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center gap-3">
        {insight.cta && (
          <button
            onClick={() =>
              handleCta(insight.cta.action, insight.cta.target, insight.cta.prompt)
            }
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[var(--blue)] text-white text-[13px] font-semibold hover:brightness-110 transition-all cursor-pointer"
          >
            {insight.cta.action === 'open_chat' ? (
              <MessageSquare className="w-3.5 h-3.5" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5" />
            )}
            {insight.cta.text}
          </button>
        )}
        {insight.secondary_cta && (
          <button
            onClick={() =>
              handleCta(
                insight.secondary_cta!.action,
                insight.secondary_cta!.target,
                insight.secondary_cta!.prompt,
              )
            }
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-[13px] font-medium text-slate-500 hover:text-slate-700 hover:bg-slate-50 transition-all cursor-pointer"
          >
            {insight.secondary_cta.text}
          </button>
        )}
      </div>
    </motion.div>
  )
}
