import type { ReactNode } from 'react'

/**
 * Chapter opener — gigantic UltraLight Roman numeral (slate-200, behind),
 * uppercase kicker "I · 你是谁", optional headline, short 2px slate rule.
 * Numeral uses Commissioner weight 200 for the dramatic thin/extrabold contrast.
 */
export function ChapterOpener({
  numeral,
  label,
  headline,
}: {
  numeral: string
  label: string
  headline?: ReactNode
}) {
  return (
    <header className="relative pt-20 md:pt-24 pb-8 mt-12 md:mt-16">
      <div
        aria-hidden
        className="absolute top-0 left-0 select-none pointer-events-none text-slate-200"
        style={{
          fontSize: 'clamp(104px, 18vw, 160px)',
          lineHeight: '0.9',
          fontWeight: 200,
          letterSpacing: '-0.04em',
        }}
      >
        {numeral}
      </div>
      <div className="relative pt-6 md:pt-8">
        <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-slate-500 mb-3">
          <span className="tabular-nums">{numeral}</span>
          <span className="mx-1.5 text-slate-300">·</span>
          <span>{label}</span>
        </p>
        {headline && (
          <h2 className="text-[32px] md:text-[40px] font-extrabold text-slate-900 leading-[1.1] tracking-[-0.02em] max-w-[28ch]">
            {headline}
          </h2>
        )}
        <div className="mt-5 w-12 h-[2px] bg-slate-900" />
      </div>
    </header>
  )
}
