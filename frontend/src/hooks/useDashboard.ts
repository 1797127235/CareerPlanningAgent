import { useQuery } from '@tanstack/react-query'
import { fetchDashboardStats } from '@/api/dashboard'
import type { DashboardStats, MetricCardData, TrendDirection } from '@/types/dashboard'

export function useDashboardStats(profileId: number | null) {
  return useQuery<DashboardStats>({
    queryKey: ['dashboard-stats', profileId],
    queryFn: () => fetchDashboardStats(profileId!),
    enabled: !!profileId,
  })
}

/**
 * Derive the 3 MetricCard view-models from raw DashboardStats.
 *
 * - 训练天数: streak_days (trend based on whether streak > 0)
 * - 练习题数: jd_diagnosis_count + review_count
 * - 平均分: average score from progress_curve
 */
export function deriveMetrics(stats: DashboardStats): MetricCardData[] {
  const totalExercises = stats.jd_diagnosis_count + stats.review_count

  // Score points from review/mock sessions only
  const reviewPoints = stats.progress_curve.filter((p) => p.type === 'review')
  const scores = reviewPoints.map((p) => p.score).filter((s) => s > 0)
  const avgScore = scores.length > 0
    ? Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 10) / 10
    : 0

  // Trend for average score: compare last 3 vs previous 3
  let scoreTrend: TrendDirection = 'flat'
  if (scores.length >= 4) {
    const recent = scores.slice(-3)
    const earlier = scores.slice(-6, -3)
    if (earlier.length > 0) {
      const recentAvg = recent.reduce((a, b) => a + b, 0) / recent.length
      const earlierAvg = earlier.reduce((a, b) => a + b, 0) / earlier.length
      if (recentAvg > earlierAvg + 1) scoreTrend = 'up'
      else if (recentAvg < earlierAvg - 1) scoreTrend = 'down'
    }
  }

  // Sparkline: last 8 score points (normalized to 0-28 range for SVG height)
  const sparkRaw = scores.slice(-8)

  // Streak sparkline: last 8 days activity (1 = active, 0 = inactive) → cumulative
  // We approximate from streak_days as a simple rising line
  const streakSpark = Array.from({ length: 8 }, (_, i) =>
    Math.min(100, Math.round((stats.streak_days / Math.max(stats.streak_days, 8)) * (i + 1) * (100 / 8)))
  )

  // Exercise count sparkline: approximate cumulative from recent_activities count per day
  const exerciseSpark = Array.from({ length: 8 }, (_, i) =>
    Math.round((totalExercises / Math.max(totalExercises, 8)) * (i + 1) * (100 / 8))
  ).map((v) => Math.min(100, v))

  return [
    {
      label: '训练天数',
      value: stats.streak_days,
      suffix: '天',
      trend: stats.streak_days > 0 ? 'up' : 'flat',
      sparkPoints: streakSpark,
      subtext: stats.streak_days > 0 ? '连续活跃中' : '今天还没训练',
    },
    {
      label: 'JD 诊断数',
      value: stats.jd_diagnosis_count,
      suffix: '次',
      trend: 'flat',
      sparkPoints: exerciseSpark,
      subtext: stats.jd_diagnosis_count > 0 ? '已积累诊断经验' : '尚未开始诊断',
    },
    {
      label: '平均分',
      value: avgScore,
      suffix: '分',
      decimals: 1,
      trend: scoreTrend,
      sparkPoints: sparkRaw,
      subtext: scores.length > 0 ? `近 ${scores.length} 次评分均值` : '暂无评分数据',
    },
  ]
}
