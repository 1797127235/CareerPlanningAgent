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
