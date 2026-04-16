import type { ReactNode } from 'react'

export function Block({
  kicker,
  title,
  children,
  className,
  accent = false,
}: {
  kicker?: ReactNode
  title?: ReactNode
  children: ReactNode
  className?: string
  /** Kept for API compatibility; BlockGrid is auto-fit so span has no effect. */
  span?: 1 | 2 | 3 | 4
  accent?: boolean
}) {
  return (
    <div
      className={[
        'bg-[var(--bg-card)] border border-[var(--line)] rounded-[var(--radius-md)] p-[var(--space-4)] transition-shadow duration-200',
        accent ? 'bg-[var(--bg-paper-2)]' : '',
        className,
      ].join(' ')}
    >
      {kicker && (
        <p className={[
          'text-[11px] font-bold uppercase tracking-[0.22em] text-[var(--chestnut)] mb-2',
          accent ? 'font-serif italic' : 'font-sans',
        ].join(' ')}>
          {kicker}
        </p>
      )}
      {title && (
        <h3 className="text-[var(--text-lg)] font-semibold text-[var(--ink-1)]">
          {title}
        </h3>
      )}
      {(kicker || title) && <div className="border-t border-[var(--line)] mt-3 mb-4" />}
      <div>{children}</div>
    </div>
  )
}
