export function SectionDivider({ numeral }: { numeral: 'II' | 'III' | 'IV' }) {
  return (
    <div className="flex items-center gap-4 my-8 md:my-12">
      <div className="flex-1 h-px bg-[var(--line)]" />
      <span className="font-serif italic text-[12px] text-[var(--ink-3)] tracking-wider">
        · {numeral} ·
      </span>
      <div className="flex-1 h-px bg-[var(--line)]" />
    </div>
  )
}
