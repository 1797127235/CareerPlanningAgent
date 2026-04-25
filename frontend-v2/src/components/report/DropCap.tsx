import type { ReactNode } from 'react'

export function DropCap({ children }: { children: ReactNode }) {
  const text = String(children)
  const first = text.charAt(0)
  const rest = text.slice(1)
  return (
    <p className="text-[17px] leading-[1.8] text-slate-700">
      <span
        className="float-left mr-3 mt-[4px] text-[64px] font-extrabold leading-[0.9] text-slate-900 tracking-[-0.04em]"
        style={{ fontFamily: 'inherit' }}
      >
        {first}
      </span>
      {rest}
    </p>
  )
}
