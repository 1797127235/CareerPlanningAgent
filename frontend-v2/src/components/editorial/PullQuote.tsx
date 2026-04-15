import type { ReactNode } from 'react'

export function PullQuote({ children, attribution }: { children: ReactNode; attribution?: string }) {
  return (
    <figure className="my-10 py-6 border-y border-[var(--line)] max-w-[58ch] mx-auto text-center">
      <blockquote className="font-serif italic text-[var(--fs-quote)] leading-[1.4] text-[var(--chestnut)]">
        "{children}"
      </blockquote>
      {attribution && (
        <figcaption className="mt-3 text-[var(--fs-caption)] uppercase tracking-[0.2em] text-[var(--ink-3)]">
          — {attribution}
        </figcaption>
      )}
    </figure>
  )
}
