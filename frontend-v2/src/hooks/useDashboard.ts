import { useQuery } from '@tanstack/react-query'
import { fetchDashboardStats } from '@/api/dashboard'
import type { DashboardStats, MetricCardData } from '@/types/dashboard'

export function useDashboardStats(profileId: number | null) {
  return useQuery<DashboardStats>({
    queryKey: ['dashboard-stats', profileId],
    queryFn: () => fetchDashboardStats(profileId!),
    enabled: !!profileId,
  })
}

/**
 * Derive the MetricCard view-models from raw DashboardStats.
 */
export function deriveMetrics(stats: DashboardStats): MetricCardData[] {
  const totalActivities =
    stats.jd_diagnosis_count +
    stats.project_count +
    stats.application_count +
    stats.interview_count

  // Streak sparkline: approximate cumulative
  const streakSpark = Array.from({ length: 8 }, (_, i) =>
    Math.min(100, Math.round((stats.streak_days / Math.max(stats.streak_days, 8)) * (i + 1) * (100 / 8)))
  )

  // Activity count sparkline
  const activitySpark = Array.from({ length: 8 }, (_, i) =>
    Math.round((totalActivities / Math.max(totalActivities, 8)) * (i + 1) * (100 / 8))
  ).map((v) => Math.min(100, v))

  return [
    {
      label: '活跃天数',
      value: stats.streak_days,
      suffix: '天',
      trend: stats.streak_days > 0 ? 'up' : 'flat',
      sparkPoints: streakSpark,
      subtext: stats.streak_days > 0 ? '连续活跃中' : '今天还没记录',
    },
    {
      label: 'JD 诊断',
      value: stats.jd_diagnosis_count,
      suffix: '次',
      trend: 'flat',
      sparkPoints: activitySpark,
      subtext: stats.jd_diagnosis_count > 0 ? '已积累诊断经验' : '尚未开始诊断',
    },
    {
      label: '项目记录',
      value: stats.project_count,
      suffix: '个',
      trend: stats.project_count > 0 ? 'up' : 'flat',
      sparkPoints: activitySpark,
      subtext: stats.project_count > 0 ? '持续补齐技能缺口' : '还没有记录项目',
    },
  ]
}
