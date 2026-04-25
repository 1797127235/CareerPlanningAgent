import type { ReactNode } from 'react'

/**
 * Reading-column wrapper for chapter body. Cap at 68ch for comfortable tracking.
 */
export function Chapter({ children }: { children: ReactNode }) {
  return (
    <section className="text-[17px] leading-[1.8] text-slate-700 max-w-[68ch]">
      {children}
    </section>
  )
}
