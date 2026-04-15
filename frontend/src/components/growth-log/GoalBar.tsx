import { useQuery } from '@tanstack/react-query'
import { ArrowRight } from 'lucide-react'
import { getGrowthDashboard } from '@/api/growthLog'

export function GoalBar() {
  const { data, isLoading } = useQuery({
    queryKey: ['growth-dashboard'],
    queryFn: getGrowthDashboard,
    staleTime: 120_000,
  })

  const dashboard = data as { has_goal?: boolean; goal?: { target_label: string }; days_since_start?: number } | undefined

  // Loading: static skeleton that holds the hero height, no spinner/pulse on big type.
  if (isLoading) {
    return <div className="py-6 md:py-8 h-[148px]" aria-hidden />
  }

  if (!dashboard?.has_goal) {
    return (
      <a href="/graph" className="group block py-6 md:py-8 cursor-pointer">
        <p className="text-[11px] font-bold tracking-[0.18em] uppercase text-slate-400 mb-3">
          方向
        </p>
        <div className="flex items-end justify-between gap-6">
          <h1 className="flex-1 min-w-0 text-[40px] md:text-[52px] lg:text-[60px] font-extrabold leading-[0.95] tracking-tight text-slate-900 group-hover:text-blue-700 transition-colors">
            还没选方向
          </h1>
          <ArrowRight className="w-6 h-6 text-slate-300 group-hover:text-blue-500 transition-colors mb-3 shrink-0" />
        </div>
        <p className="mt-4 text-[13px] text-slate-500 max-w-[52ch]">
          去岗位图谱浏览方向，挑一个作为成长目标。之后每条记录都会挂在它下面。
        </p>
      </a>
    )
  }

  const days = dashboard.days_since_start ?? 0

  return (
    <div className="py-6 md:py-8">
      <p className="flex items-center gap-2 text-[11px] font-bold tracking-[0.18em] uppercase text-slate-400 mb-3">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-500" />
        当前方向
      </p>
      <div className="flex items-end justify-between gap-6">
        <h1 className="flex-1 min-w-0 text-[40px] md:text-[52px] lg:text-[60px] font-extrabold leading-[0.95] tracking-tight text-slate-900">
          {dashboard.goal?.target_label}
        </h1>
        {days > 0 && (
          <div className="flex items-baseline gap-1.5 shrink-0">
            <span className="text-[56px] md:text-[72px] lg:text-[88px] font-extrabold leading-[0.85] tracking-tight text-slate-900 tabular-nums">
              {days}
            </span>
            <span className="text-[13px] font-semibold uppercase tracking-[0.2em] text-slate-400 pb-2">
              天
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
