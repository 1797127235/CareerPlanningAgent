import { ArrowUpRight } from 'lucide-react'
import { PaperCard } from '@/components/editorial'

export interface Recommendation {
  role_id: string
  label: string
  reason?: string
  zone?: string
  replacement_pressure?: number
}

const ZONE_STYLE: Record<string, string> = {
  safe:       'bg-emerald-50 text-emerald-600',
  leverage:   'bg-blue-50 text-blue-600',
  transition: 'bg-amber-50 text-amber-600',
  danger:     'bg-red-50 text-red-500',
}

const ZONE_TEXT: Record<string, string> = {
  safe:       '安全区',
  leverage:   '杠杆区',
  transition: '转型区',
  danger:     '风险区',
}

export function RecommendationCard({
  rec,
  onExplore,
}: {
  rec: Recommendation
  onExplore?: () => void
}) {
  const zoneStyle = rec.zone ? (ZONE_STYLE[rec.zone] || 'bg-slate-100 text-slate-600') : ''
  const zoneText = rec.zone ? (ZONE_TEXT[rec.zone] || rec.zone) : ''
  const rp = rec.replacement_pressure ?? 50
  const rpColor = rp < 30 ? 'bg-emerald-400' : rp < 55 ? 'bg-amber-400' : 'bg-rose-400'
  const rpLabel = rp < 30 ? 'AI安全' : rp < 55 ? 'AI中等' : 'AI风险'

  return (
    <PaperCard
      className={onExplore ? 'cursor-pointer hover:shadow-[var(--shadow-chapter)] transition-shadow' : ''}
      onClick={onExplore}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="font-sans text-[length:var(--fs-body-lg)] font-medium text-[var(--ink-1)] truncate">
            {rec.label}
          </p>
          {(zoneText || rec.replacement_pressure != null) && (
            <div className="flex items-center gap-2 mt-1">
              {zoneText && (
                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${zoneStyle}`}>
                  {zoneText}
                </span>
              )}
              {rec.replacement_pressure != null && (
                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full text-white ${rpColor}`}>
                  {rpLabel}
                </span>
              )}
            </div>
          )}
          {rec.reason && (
            <p className="mt-1 text-[length:var(--fs-body)] text-[var(--ink-2)] line-clamp-2">
              {rec.reason}
            </p>
          )}
        </div>
        {onExplore && <ArrowUpRight className="w-4 h-4 text-[var(--ink-3)] shrink-0 mt-1" />}
      </div>
    </PaperCard>
  )
}
