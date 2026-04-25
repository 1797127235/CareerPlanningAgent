import type { ReactNode } from 'react'

/**
 * Magazine pull quote — no Literata italic (Commissioner has no italic on GF).
 * Sells "this is a quote" via scale + left rule + attribution kicker below.
 */
export function PullQuote({
  children,
  attribution,
}: {
  children: ReactNode
  attribution?: ReactNode
}) {
  return (
    <blockquote className="my-10 pl-6 border-l-2 border-slate-300">
      <p className="text-[22px] leading-[1.4] text-slate-900 tracking-[-0.01em] font-medium">
        {children}
      </p>
      {attribution && (
        <p className="mt-3 text-[10px] font-bold uppercase tracking-[0.22em] text-slate-400">
          {attribution}
        </p>
      )}
    </blockquote>
  )
}
