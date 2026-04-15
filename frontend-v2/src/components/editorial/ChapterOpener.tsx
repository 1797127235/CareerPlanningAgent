import type { ReactNode } from 'react'

export function ChapterOpener({ numeral, title }: { numeral: string; title: ReactNode }) {
  return (
    <div className="relative py-24 md:py-32 mb-8">
      <span
        aria-hidden
        className="absolute left-0 top-1/2 -translate-y-1/2 font-serif font-light text-[160px] md:text-[220px] leading-none tracking-tighter select-none pointer-events-none"
        style={{ color: 'var(--line)', zIndex: 0 }}
      >
        {numeral}
      </span>
      <div className="relative z-10 max-w-[18ch]">
        <h1 className="font-display font-medium text-[var(--fs-display-xl)] leading-[var(--lh-display)] text-[var(--ink-1)] tracking-tight">
          {title}
        </h1>
      </div>
    </div>
  )
}
