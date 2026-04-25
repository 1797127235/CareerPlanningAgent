import type { ReactNode } from 'react'

export function BlockGrid({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={['grid gap-[var(--space-4)] items-start', className].join(' ')}
      style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}
    >
      {children}
    </div>
  )
}
