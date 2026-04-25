import { ArrowUpRight } from 'lucide-react'
import { PaperCard } from '@/components/editorial'

export interface Recommendation {
  role_id: string
  label: string
  reason?: string
}

export function RecommendationCard({
  rec,
  onExplore,
}: {
  rec: Recommendation
  onExplore?: () => void
}) {
  return (
    <PaperCard
      className={onExplore ? 'cursor-pointer hover:shadow-[var(--shadow-chapter)] transition-shadow' : ''}
      onClick={onExplore}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-sans text-[length:var(--fs-body-lg)] font-medium text-[var(--ink-1)]">
            {rec.label}
          </p>
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
