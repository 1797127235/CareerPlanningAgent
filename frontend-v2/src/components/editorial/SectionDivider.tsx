interface SectionDividerProps {
  numeral: string
  className?: string
  lineClassName?: string
  labelClassName?: string
}

export function SectionDivider({ numeral, className = '', lineClassName = '', labelClassName = '' }: SectionDividerProps) {
  return (
    <div className={['relative my-12 md:my-14 flex items-center justify-center', className].filter(Boolean).join(' ')}>
      <div className="absolute inset-0 flex items-center">
        <div className={['w-full border-t border-[var(--line)]', lineClassName].filter(Boolean).join(' ')} />
      </div>
      <span
        className={['relative bg-[var(--bg-paper)] px-4 font-serif italic text-[length:var(--fs-body)] text-[var(--ink-3)]', labelClassName].filter(Boolean).join(' ')}
        style={{ fontFamily: 'var(--font-serif)' }}
      >
        {numeral}
      </span>
    </div>
  )
}
