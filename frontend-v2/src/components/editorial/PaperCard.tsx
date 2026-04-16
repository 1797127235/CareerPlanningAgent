import type { HTMLAttributes, ReactNode } from 'react'

type PaperCardProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode
  className?: string
}

export function PaperCard({ children, className = '', onClick, onKeyDown, ...rest }: PaperCardProps) {
  const isInteractive = typeof onClick === 'function'
  const handleKeyDown = isInteractive
    ? (e: React.KeyboardEvent<HTMLDivElement>) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick?.(e as unknown as React.MouseEvent<HTMLDivElement>)
        }
        onKeyDown?.(e)
      }
    : onKeyDown

  return (
    <div
      {...rest}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      role={isInteractive ? 'button' : rest.role}
      tabIndex={isInteractive ? 0 : rest.tabIndex}
      className={[
        'bg-[var(--bg-card)] rounded-lg p-5 md:p-7',
        'shadow-[0_1px_2px_var(--warm-shadow-1),0_4px_12px_var(--warm-shadow-2)]',
        'transition-[box-shadow,background-color] duration-200',
        isInteractive ? 'hover:shadow-[var(--shadow-float)] hover:bg-[var(--bg-card-hover)] active:scale-[0.99]' : '',
        className,
      ].join(' ')}
    >
      {children}
    </div>
  )
}
