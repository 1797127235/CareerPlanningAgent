import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Activity,
  Briefcase,
  CheckCircle2,
  Target,
  Mic,
  type LucideIcon,
} from 'lucide-react'
import { getInsights, type InsightItem } from '@/api/growthLog'

const ICON_MAP: Record<string, LucideIcon> = {
  activity: Activity,
  briefcase: Briefcase,
  'check-circle': CheckCircle2,
  target: Target,
  mic: Mic,
}

const LEVEL_STYLES = {
  normal: {
    border: 'border-transparent',
    iconBg: 'bg-[var(--blue)]/[0.08]',
    iconColor: 'text-[var(--blue)]',
  },
  warning: {
    border: 'border-amber-400/30',
    iconBg: 'bg-amber-400/[0.08]',
    iconColor: 'text-amber-500',
  },
  highlight: {
    border: 'border-[var(--blue)]/20',
    iconBg: 'bg-[var(--blue)]/[0.12]',
    iconColor: 'text-[var(--blue)]',
  },
}

function InsightCard({ item, index }: { item: InsightItem; index: number }) {
  const navigate = useNavigate()
  const Icon = ICON_MAP[item.icon] || Activity
  const styles = LEVEL_STYLES[item.level]

  return (
    <motion.button
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06, duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
      onClick={() => item.link && navigate(item.link)}
      className={[
        'flex-shrink-0 w-[260px] text-left glass p-4 cursor-pointer',
        'border',
        styles.border,
      ].join(' ')}
    >
      <div className="g-inner">
        <div className="flex items-start gap-3">
          <div className={['shrink-0 w-8 h-8 rounded-lg flex items-center justify-center', styles.iconBg].join(' ')}>
            <Icon className={['w-4 h-4', styles.iconColor].join(' ')} />
          </div>
          <div className="min-w-0">
            <p className="text-[13px] font-semibold text-[var(--text-1)] leading-snug">
              {item.headline}
            </p>
            {item.detail && (
              <p className="mt-1 text-[12px] text-[var(--text-2)] leading-relaxed">
                {item.detail}
              </p>
            )}
          </div>
        </div>
      </div>
    </motion.button>
  )
}

export function InsightCards() {
  const { data, isLoading } = useQuery({
    queryKey: ['growth-insights'],
    queryFn: getInsights,
    staleTime: 60_000,
  })

  const insights = data?.insights ?? []

  if (isLoading) {
    return (
      <div className="flex gap-3 overflow-x-auto pb-1">
        {[...Array(3)].map((_, i) => (
          <div
            key={i}
            className="flex-shrink-0 w-[260px] h-[80px] glass-static rounded-[var(--radius-md)]"
          />
        ))}
      </div>
    )
  }

  if (insights.length === 0) {
    return null
  }

  return (
    <div className="flex gap-3 overflow-x-auto pb-1 -mx-4 px-4 md:-mx-8 md:px-8">
      {insights.map((item, i) => (
        <InsightCard key={`${item.type}-${i}`} item={item} index={i} />
      ))}
    </div>
  )
}
