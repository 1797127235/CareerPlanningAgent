import { useQuery } from '@tanstack/react-query'
import { Flag, ArrowRight } from 'lucide-react'
import { getGrowthDashboard } from '@/api/growthLog'

export function GoalBar() {
  const { data, isLoading } = useQuery({
    queryKey: ['growth-dashboard'],
    queryFn: getGrowthDashboard,
    staleTime: 120_000,
  })

  const dashboard = data as { has_goal?: boolean; goal?: { target_label: string }; days_since_start?: number } | undefined

  // 加载中：占位，不渲染任何引导
  if (isLoading) {
    return <div className="rounded-md border border-[var(--line)] bg-[var(--bg-card)] p-4 mb-4 h-[52px] animate-pulse" />
  }

  if (!dashboard?.has_goal) {
    return (
      <div className="rounded-md border border-[var(--line)] bg-[var(--bg-card)] p-4 mb-4">
        <a href="/graph"
          className="flex items-center gap-3 cursor-pointer group">
          <div className="w-8 h-8 rounded-md bg-[var(--bg-paper)] flex items-center justify-center shrink-0 border border-[var(--line)]">
            <Flag className="w-4 h-4 text-[var(--chestnut)]" />
          </div>
          <div className="flex-1">
            <p className="text-[13px] font-semibold text-[var(--ink-1)] group-hover:text-[var(--chestnut)] transition-colors">
              选一个发展方向
            </p>
            <p className="text-[11px] text-[var(--ink-3)]">去岗位图谱浏览方向，选一个作为成长目标</p>
          </div>
          <ArrowRight className="w-4 h-4 text-[var(--line)] group-hover:text-[var(--chestnut)] transition-colors shrink-0" />
        </a>
      </div>
    )
  }

  return (
    <div className="rounded-md border border-[var(--line)] bg-[var(--bg-card)] p-4 mb-4">
      <div className="flex items-center gap-3">
        <div className="w-2.5 h-2.5 rounded-full bg-[var(--moss)] shrink-0" />
        <p className="text-[17px] font-bold text-[var(--ink-1)]">{dashboard.goal?.target_label}</p>
        {(dashboard.days_since_start ?? 0) > 0 && (
          <span className="text-[12px] text-[var(--ink-3)] ml-auto tabular-nums">陪你 {dashboard.days_since_start} 天了</span>
        )}
      </div>
    </div>
  )
}
