import { Pencil } from 'lucide-react'
import { PaperCard } from '@/components/editorial'
import type { Education } from '@/types/profile'

export function EducationCard({
  education,
  onEdit,
}: {
  education?: Education
  onEdit?: () => void
}) {
  const hasData = education?.school || education?.major || education?.degree
  return (
    <PaperCard className="relative group">
      {onEdit && (
        <button
          onClick={onEdit}
          className="absolute top-4 right-4 p-1.5 text-[var(--ink-3)] hover:text-[var(--ink-1)] opacity-0 group-hover:opacity-100 transition-opacity"
          aria-label="编辑"
        >
          <Pencil className="w-4 h-4" />
        </button>
      )}
      {hasData ? (
        <div className="space-y-1">
          <p className="font-sans text-[length:var(--fs-body-lg)] font-medium text-[var(--ink-1)]">
            {education?.school}
          </p>
          <p className="font-sans text-[length:var(--fs-body)] text-[var(--ink-2)]">
            {education?.major} · {education?.degree}
          </p>
        </div>
      ) : (
        <p className="text-[length:var(--fs-body)] text-[var(--ink-3)] italic">
          还没有教育背景记录 —— 先讲讲学校和专业吧。
        </p>
      )}
    </PaperCard>
  )
}
