import type { ReactNode } from 'react'

export function Callout({
  tone = 'accent',
  children,
}: {
  tone?: 'accent' | 'warn'
  children: ReactNode
}) {
  const bg = tone === 'warn' ? 'bg-[var(--ember-soft)]' : 'bg-[var(--chestnut-soft)]'
  return (
    <div className={['rounded-[var(--radius-md)] p-[var(--space-3)] text-[var(--text-base)] text-[var(--ink-1)]', bg].join(' ')}>
      {children}
    </div>
  )
}
