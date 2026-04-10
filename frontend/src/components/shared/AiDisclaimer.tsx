import { Info } from 'lucide-react'

export function AiDisclaimer() {
  return (
    <p className="stat-cap flex items-center gap-1.5 text-[12px] text-[var(--text-3)] mt-3 w-fit">
      <Info className="w-3.5 h-3.5 shrink-0" />
      基于当前数据，仅供参考
    </p>
  )
}
