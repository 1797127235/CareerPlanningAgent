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
    return <div className="glass-static rounded-2xl p-4 mb-4 h-[52px] animate-pulse" />
  }

  if (!dashboard?.has_goal) {
    return (
      <div className="glass-static rounded-2xl p-4 mb-4">
        <a href="/graph"
          className="flex items-center gap-3 cursor-pointer group">
          <div className="w-8 h-8 rounded-lg bg-blue-500/15 flex items-center justify-center shrink-0">
            <Flag className="w-4 h-4 text-blue-600" />
          </div>
          <div className="flex-1">
            <p className="text-[13px] font-semibold text-slate-800 group-hover:text-blue-700 transition-colors">
              选一个发展方向
            </p>
            <p className="text-[11px] text-slate-500">去岗位图谱浏览方向，选一个作为成长目标</p>
          </div>
          <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-blue-500 transition-colors shrink-0" />
        </a>
      </div>
    )
  }

  return (
    <div className="glass-static rounded-2xl p-4 mb-4">
      <div className="flex items-center gap-3">
        <div className="w-2.5 h-2.5 rounded-full bg-blue-500 shrink-0" />
        <p className="text-[17px] font-bold text-slate-900">{dashboard.goal?.target_label}</p>
        {(dashboard.days_since_start ?? 0) > 0 && (
          <span className="text-[12px] text-slate-400 ml-auto tabular-nums">已坚持 {dashboard.days_since_start} 天</span>
        )}
      </div>
    </div>
  )
}
