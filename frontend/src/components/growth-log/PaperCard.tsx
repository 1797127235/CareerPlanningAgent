import type { ReactNode } from 'react'

interface PaperCardProps {
  children: ReactNode
  className?: string
  padded?: boolean
}

export function PaperCard({ children, className = '', padded = true }: PaperCardProps) {
  return (
    <div
      className={[
        'rounded-md border',
        'bg-[var(--bg-card)] border-[var(--line)]',
        'shadow-[0_1px_2px_rgba(60,40,20,0.04),0_4px_12px_rgba(60,40,20,0.05)]',
        padded ? 'p-6 md:p-8' : '',
        className,
      ].join(' ')}
    >
      {children}
    </div>
  )
}
