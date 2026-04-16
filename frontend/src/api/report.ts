import { rawFetch } from '@/api/client'

export interface ReportListItem {
  id: number
  report_key: string
  title: string
  summary: string
  created_at: string
  profile_id?: number | null
  match_score?: number | null
}

export interface ReportNarrative {
  summary: string
  comparison: string | null
  chapters: Partial<Record<string, string>>
  actions: string[]
}

export interface ReportChapter {
  key: string
  title: string
  subtitle?: string
  has_data: boolean
  locked_hint?: string
  data: Record<string, unknown>
}

export interface ReportDetail {
  id: number
  report_key: string
  title: string
  summary: string
  data: {
    version?: string
    report_version?: number
    markdown?: string
    narrative?: ReportNarrative
    chapters?: ReportChapter[]
    match_score?: number
    student_name?: string
    target_job?: string
    profile_id?: number
    created_at?: string
    [key: string]: unknown
  }
  created_at: string
  updated_at: string
}

export async function fetchReportList(): Promise<ReportListItem[]> {
  return rawFetch<ReportListItem[]>('/report/')
}

export async function fetchReportDetail(reportId: number): Promise<ReportDetail> {
  return rawFetch<ReportDetail>(`/report/${reportId}`)
}

export async function generateReport(): Promise<ReportDetail> {
  return rawFetch('/report/generate', {
    method: 'POST',
  })
}

// ── v2 narrative shape ─────────────────────────────────────────────────────
// Same backend endpoint as generateReport; just a precise type for the
// four-chapter narrative layout used by the rewritten ReportPage.
export interface ReportV2Data {
  version: string
  report_type: string
  student: { user_id: number; profile_id: number }
  target: { node_id: string; label: string; zone?: string }
  match_score: number
  four_dim: {
    foundation: number | null
    skills: number | null
    qualities: number | null
    potential: number | null
  }
  narrative: string
  /** User-written overrides, keyed "chapter-1" .. "chapter-4".
   * When present, chapters prefer the override text over AI-generated prose. */
  chapter_narratives?: Record<string, string>
  diagnosis: Array<{
    source: string
    source_type: string
    source_id: number
    current_text: string
    status: 'pass' | 'needs_improvement'
    highlight: string
    issues: string[]
    suggestion: string
  }>
  market: {
    demand_change_pct: number | null
    salary_cagr: number | null
    salary_p50: number
    timing: string
    timing_label: string
  }
  market_narrative?: string
  skill_gap: {
    core: { total: number; matched: number; pct: number; practiced_count: number; claimed_count: number }
    important: { total: number; matched: number; pct: number; practiced_count: number; claimed_count: number }
    bonus: { total: number; matched: number; pct: number; practiced_count: number; claimed_count: number }
    top_missing: Array<{
      name: string
      freq: number
      tier: string
      covered_by_project?: boolean
      fill_path?: string
    }>
    matched_skills: Array<{ name: string; tier: string; status: string; freq: number }>
    has_project_data: boolean
  }
  growth_curve: Array<{ date: string; score: number }>
  action_plan: {
    stages: PlanStage[]
    skills: PlanActionItem[]
    project: PlanActionItem[]
    job_prep: PlanActionItem[]
  }
  delta: {
    prev_score: number
    score_change: number
    prev_date: string
    gained_skills: string[]
    still_missing: string[]
    plan_progress: { done: number; total: number } | null
    next_action: string | null
  } | null
  soft_skills: Record<string, unknown>
  career_alignment: {
    observations: string
    alignments: Array<{
      node_id: string
      label: string
      score: number
      evidence: string
      gap: string
    }>
    cannot_judge: string[]
  }
  differentiation_advice: string
  ai_impact_narrative: string
  project_recommendations: Array<Record<string, unknown>>
  project_mismatch: boolean
  generated_at: string
}

export async function generateReportV2(): Promise<ReportDetail & { data: ReportV2Data }> {
  const detail = await generateReport()
  return detail as ReportDetail & { data: ReportV2Data }
}

export async function deleteReport(reportId: number): Promise<void> {
  await rawFetch<{ ok: boolean }>(`/report/${reportId}`, { method: 'DELETE' })
}

export async function editReport(
  reportId: number,
  edits: { narrative_summary?: string; chapter_narratives?: Record<string, string> },
): Promise<{ ok: boolean }> {
  return rawFetch(`/report/${reportId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(edits),
  })
}

export async function polishReport(reportId: number): Promise<{ ok: boolean; polished: Record<string, string> }> {
  return rawFetch(`/report/${reportId}/polish`, { method: 'POST' })
}

// ── Plan (staged action plan with persistent checks) ─────────────────────────

export interface PlanActionItem {
  id: string
  type: 'skill' | 'project' | 'job_prep'
  sub_type?: 'validate' | 'learn'
  text: string
  tag: string
  skill_name?: string
  priority: 'high' | 'medium'
  done: boolean
  phase?: number
  deliverable?: string
}

export interface PlanStage {
  stage: number
  label: string
  duration: string
  milestone: string
  items: PlanActionItem[]
}

export interface PlanData {
  stages: PlanStage[]
  checked: Record<string, boolean>
}

export async function fetchPlan(reportId: number): Promise<PlanData> {
  return rawFetch<PlanData>(`/report/${reportId}/plan`)
}

export async function updatePlanCheck(
  reportId: number,
  itemId: string,
  done: boolean,
): Promise<{ ok: boolean }> {
  return rawFetch(`/report/${reportId}/plan/check`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ item_id: itemId, done }),
  })
}
