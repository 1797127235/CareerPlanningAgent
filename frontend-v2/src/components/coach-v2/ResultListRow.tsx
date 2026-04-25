import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Trash2 } from 'lucide-react'
import { PaperCard, Kicker } from '@/components/editorial'
import { deleteCoachResult } from '@/api/coach'
import { typeLabelOf } from '@/lib/resultTypeBuckets'
import type { CoachResultListItem } from '@/types/coach'

export function ResultListRow({ item }: { item: CoachResultListItem }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const deleteMut = useMutation({
    mutationFn: () => deleteCoachResult(item.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['coach-results'] })
    },
  })

  const matchScore = item.metadata?.match_score as number | undefined

  return (
    <PaperCard
      className="group relative cursor-pointer"
      onClick={() => navigate(`/coach/result/${item.id}`)}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-3 mb-2">
            <Kicker>{typeLabelOf(item.result_type)}</Kicker>
            <span className="font-sans text-[length:var(--fs-caption)] text-[var(--ink-3)] shrink-0">
              {item.created_at?.slice(0, 10)}
            </span>
          </div>

          <h2 className="font-display font-medium text-[length:var(--fs-display-sm)] leading-[var(--lh-display)] text-[var(--ink-1)] tracking-tight max-w-[28ch] mb-2">
            {item.title}
          </h2>

          <p className="font-sans text-[length:var(--fs-body)] leading-[var(--lh-body-zh)] text-[var(--ink-2)] line-clamp-2 max-w-[58ch]">
            {item.summary}
          </p>

          {matchScore != null && (
            <div className="mt-3">
              <span className="inline-block font-serif italic text-[length:var(--fs-body-sm)] text-[var(--chestnut)]">
                匹配度 {matchScore}%
              </span>
            </div>
          )}
        </div>
      </div>

      <button
        onClick={(e) => {
          e.stopPropagation()
          deleteMut.mutate()
        }}
        className="absolute top-4 right-4 p-2 text-[var(--ink-3)] hover:text-[var(--ember)] opacity-0 group-hover:opacity-100 transition-opacity"
        aria-label="删除"
      >
        <Trash2 className="w-4 h-4" />
      </button>
    </PaperCard>
  )
}
