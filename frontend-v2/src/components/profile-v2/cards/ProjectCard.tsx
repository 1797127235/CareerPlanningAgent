import { Pencil } from 'lucide-react'
import { PaperCard, PullQuote } from '@/components/editorial'

export interface ProjectItem {
  name?: string
  description?: string
  tech_stack?: string[]
}

export function ProjectCard({
  project,
  onEdit,
}: {
  project: string | ProjectItem
  onEdit?: () => void
}) {
  const isString = typeof project === 'string'
  const name = isString ? '' : project.name || ''
  const description = isString ? project : project.description || ''
  const techStack = isString ? [] : project.tech_stack || []
  const hasQuote = description.length > 30

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
      {name && (
        <p className="font-sans text-[var(--fs-body-lg)] font-medium text-[var(--ink-1)] mb-2">
          {name}
        </p>
      )}
      {hasQuote ? (
        <PullQuote>{description}</PullQuote>
      ) : (
        <p className="text-[var(--fs-body)] text-[var(--ink-2)] leading-[var(--lh-body-zh)]">
          {description}
        </p>
      )}
      {techStack.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {techStack.map((t) => (
            <span
              key={t}
              className="px-2 py-1 rounded-full text-[11px] font-medium bg-[var(--bg-paper)] text-[var(--ink-2)] border border-[var(--line)]"
            >
              {t}
            </span>
          ))}
        </div>
      )}
    </PaperCard>
  )
}
