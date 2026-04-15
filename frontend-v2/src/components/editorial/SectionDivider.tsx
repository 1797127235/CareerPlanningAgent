export function SectionDivider({ numeral }: { numeral: string }) {
  return (
    <div className="relative my-16 flex items-center justify-center">
      <div className="absolute inset-0 flex items-center">
        <div className="w-full border-t border-[var(--line)]" />
      </div>
      <span className="relative bg-[var(--bg-paper)] px-4 font-serif italic text-[length:var(--fs-body)] text-[var(--ink-3)]">
        {numeral}
      </span>
    </div>
  )
}
