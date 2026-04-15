import type { ReactNode } from 'react'

export function PaperCard({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={[
        'bg-[var(--bg-card)] rounded-lg p-5 md:p-7',
        'shadow-[0_1px_2px_var(--warm-shadow-1),0_4px_12px_var(--warm-shadow-2)]',
        className,
      ].join(' ')}
    >
      {children}
    </div>
  )
}
