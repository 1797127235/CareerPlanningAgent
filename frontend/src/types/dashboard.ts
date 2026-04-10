/* ── Dashboard API types ── */

export interface ChecklistProgress {
  total: number
  passed: number
  progress: number
  jd_title: string
}

export interface RecentActivity {
  type: 'jd_diagnosis' | 'interview_review' | 'mock_interview'
  title: string
  date: string
  id: number
}

export interface ProgressPoint {
  type: 'jd' | 'review'
  date: string
  score: number
  /** Per-dimension scores for this data point (review only) */
  dimensions?: Record<string, number>
}

export interface DimensionAvg {
  name: string
  avg_score: number
  count: number
  trend: 'up' | 'down' | 'flat'
}

export interface DimensionSummary {
  dimensions: DimensionAvg[]
  weakest: string[]
}

/** GET /api/dashboard/stats?profile_id=N */
export interface DashboardStats {
  jd_diagnosis_count: number
  review_count: number
  checklist_progress: ChecklistProgress | null
  streak_days: number
  recent_activities: RecentActivity[]
  progress_curve: ProgressPoint[]
  dimension_summary: DimensionSummary
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
  /** Last N score values for sparkline rendering */
  sparkPoints?: number[]
  /** Subtext shown below the value */
  subtext?: string
}
