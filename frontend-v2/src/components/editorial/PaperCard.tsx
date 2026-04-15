import type { ReactNode } from 'react'

export function PaperCard({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={[
        'bg-[var(--bg-card)] rounded-sm',
        'shadow-[var(--shadow-paper)]',
        'p-6 md:p-8',
        className,
      ].join(' ')}
    >
      {children}
    </div>
  )
}
