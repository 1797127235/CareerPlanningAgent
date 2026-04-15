import { PaperCard } from '@/components/editorial'
import type { Internship } from '@/types/profile'

export function InternshipCard({ internship }: { internship: Internship }) {
  return (
    <PaperCard>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-sans text-[length:var(--fs-body-lg)] font-medium text-[var(--ink-1)]">
            {internship.company}
          </p>
          <p className="font-sans text-[length:var(--fs-body)] text-[var(--ink-2)]">
            {internship.role}
            {internship.duration ? ` · ${internship.duration}` : ''}
          </p>
        </div>
      </div>
      {internship.highlights && (
        <p className="mt-3 text-[length:var(--fs-body)] text-[var(--ink-2)] leading-[var(--lh-body-zh)]">
          {internship.highlights}
        </p>
      )}
      {internship.tech_stack && internship.tech_stack.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {internship.tech_stack.map((t) => (
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
