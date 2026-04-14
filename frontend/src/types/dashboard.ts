/* ── Dashboard API types ── */

export interface RecentActivity {
  type: 'jd_diagnosis' | 'project' | 'application' | 'interview'
  title: string
  date: string
  id: number
}

/** GET /api/dashboard/stats?profile_id=N */
export interface DashboardStats {
  jd_diagnosis_count: number
  project_count: number
  application_count: number
  interview_count: number
  streak_days: number
  recent_activities: RecentActivity[]
}

/* ── Derived view-model for MetricCard ── */

export type TrendDirection = 'up' | 'down' | 'flat'

export interface MetricCardData {
  label: string
  value: number
  /** Optional suffix like "天" or "分" */
  suffix?: string
  trend: TrendDirection
  /** Display as decimal (e.g. 72.5) */
  decimals?: number
  /** Last N values for sparkline rendering */
  sparkPoints?: number[]
  /** Subtext shown below the value */
  subtext?: string
}
