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
      className="rounded-xl p-5 mb-5 border-l-4"
      style={{ background: 'var(--bg-card)', borderColor: 'var(--chestnut)', borderLeftWidth: 4, borderLeftStyle: 'solid' }}
    >
      <div className="flex items-center gap-2 mb-3">
        <div className="w-7 h-7 rounded-lg flex items-center justify-center"
          style={{ background: 'rgba(184,92,56,0.10)' }}>
          <Compass className="w-4 h-4" style={{ color: 'var(--chestnut)' }} />
        </div>
        <span className="text-[13px] font-bold" style={{ color: 'var(--ink-1)' }}>智析教练发现</span>
      </div>

      <p className="text-[14px] leading-relaxed mb-3" style={{ color: 'var(--ink-1)' }}>
        {insight.insight}
      </p>

      {insight.evidence && insight.evidence.length > 0 && (
        <div className="mb-4 space-y-1.5">
          {insight.evidence.map((item, idx) => (
            <div key={idx} className="flex items-start gap-2">
              <Lightbulb className="w-3.5 h-3.5 mt-0.5 shrink-0" style={{ color: 'var(--chestnut)' }} />
              <span className="text-[12px] leading-relaxed" style={{ color: 'var(--ink-2)' }}>{item}</span>
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
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-white text-[13px] font-semibold hover:brightness-110 transition-all cursor-pointer"
            style={{ background: 'var(--chestnut)' }}
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
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-[13px] font-medium transition-all cursor-pointer"
            style={{ color: 'var(--ink-2)' }}
          >
            {insight.secondary_cta.text}
          </button>
        )}
      </div>
    </motion.div>
  )
}
