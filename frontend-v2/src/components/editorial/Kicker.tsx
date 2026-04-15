import type { ReactNode } from 'react'

export function Kicker({ children }: { children: ReactNode }) {
  return (
    <p className="font-sans text-[11px] font-bold uppercase tracking-[0.22em] text-[var(--chestnut)] mb-3">
      {children}
    </p>
  )
}
