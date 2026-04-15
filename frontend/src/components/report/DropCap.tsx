import type { ReactNode } from 'react'

/**
 * Editorial drop cap — first character is floated and set at ~4x scale.
 * Works for Latin and CJK characters. No serif fallback needed: Commissioner
 * ExtraBold at size 64 with tight tracking feels like a magazine lead.
 */
export function DropCap({ children }: { children: ReactNode }) {
  return (
    <p className="text-[17px] leading-[1.8] text-slate-700 first-letter:float-left first-letter:mr-3 first-letter:mt-[4px] first-letter:text-[64px] first-letter:font-extrabold first-letter:leading-[0.9] first-letter:text-slate-900 first-letter:tracking-[-0.04em]">
      {children}
    </p>
  )
}
