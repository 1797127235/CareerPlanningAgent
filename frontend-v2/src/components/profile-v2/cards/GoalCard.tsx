import { Target, ArrowUpRight } from 'lucide-react'
import { PaperCard } from '@/components/editorial'
import type { CareerGoal } from '@/types/profile'

export function GoalCard({
  goal,
  onExplore,
  onChange,
}: {
  goal: CareerGoal
  onExplore?: () => void
  onChange?: () => void
}) {
  return (
    <PaperCard>
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-full bg-[var(--bg-paper)] flex items-center justify-center shrink-0">
          <Target className="w-5 h-5 text-[var(--chestnut)]" />
        </div>
        <div className="flex-1">
          <p className="font-sans text-[length:var(--fs-body-lg)] font-medium text-[var(--ink-1)]">
            {goal.target_label}
          </p>
          {goal.from_node_label && (
            <p className="text-[length:var(--fs-body)] text-[var(--ink-2)]">
              从 {goal.from_node_label} 过来
            </p>
          )}
          <div className="mt-4 flex flex-wrap gap-3">
            {onExplore && (
              <button
                onClick={onExplore}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full border border-[var(--line)] text-[var(--ink-1)] text-[13px] font-medium hover:bg-[var(--line)]/10 transition-colors"
              >
                去图谱看路径 <ArrowUpRight className="w-3.5 h-3.5" />
              </button>
            )}
            {onChange && (
              <button
                onClick={onChange}
                className="inline-flex items-center px-4 py-2 rounded-full text-[13px] font-medium text-[var(--ink-3)] hover:text-[var(--ink-1)] transition-colors"
              >
                换个方向
              </button>
            )}
          </div>
        </div>
      </div>
    </PaperCard>
  )
}
