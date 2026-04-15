import type { ReactNode } from 'react'

interface ChapterProps {
  numeral: 'I' | 'II' | 'III' | 'IV'
  label: string
  title: ReactNode
  intro?: ReactNode
  children: ReactNode
}

export function Chapter({ numeral, label, title, intro, children }: ChapterProps) {
  return (
    <section className="relative py-16 md:py-24">
      {/* CHAPTER N · 标签 */}
      <div className="flex items-center gap-3 mb-6">
        <span className="font-serif text-[11px] tracking-[0.2em] uppercase text-[var(--chestnut)]">
          Chapter {numeral} · {label}
        </span>
        <div className="flex-1 h-px bg-[var(--line)]" />
      </div>

      {/* Hero title */}
      <h2 className="font-display text-[clamp(28px,4vw,44px)] font-medium leading-[1.25] text-[var(--ink-1)] tracking-tight max-w-[20ch]">
        {title}
      </h2>

      {/* Intro */}
      {intro && (
        <p className="mt-4 font-sans text-[15px] leading-[1.7] text-[var(--ink-2)] max-w-[68ch]">
          {intro}
        </p>
      )}

      {/* Body */}
      <div className="mt-10">{children}</div>
    </section>
  )
}
