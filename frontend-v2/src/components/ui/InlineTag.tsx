import type { ReactNode } from 'react'

export function InlineTag({
  children,
  tone = 'neutral',
}: {
  children: ReactNode
  tone?: 'neutral' | 'accent' | 'warn'
}) {
  const toneCls =
    tone === 'accent'
      ? 'border-[var(--chestnut)] text-[var(--chestnut)] bg-[var(--chestnut-soft)]'
      : tone === 'warn'
        ? 'border-[var(--ember)] text-[var(--ember)] bg-[var(--ember-soft)]'
        : 'border-[var(--line)] text-[var(--ink-2)] bg-transparent'

  return (
    <span
      className={[
        'inline-flex items-center px-2 py-0.5 rounded-[var(--radius-pill)] border text-[var(--text-xs)]',
        toneCls,
      ].join(' ')}
    >
      {children}
    </span>
  )
}
