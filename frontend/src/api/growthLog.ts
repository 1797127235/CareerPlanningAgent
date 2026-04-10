import { rawFetch } from '@/api/client'

const BASE = '/growth-log'

/* ── Types ── */

export interface GrowthEvent {
  id: number
  event_type: 'project_completed' | 'interview_done' | 'learning_completed' | 'skill_added'
  source_table: string
  source_id: number
  summary: string
  skills_delta: { added?: string[]; improved?: string[] }
  readiness_before: number | null
  readiness_after: number | null
  created_at: string
}

export interface ProjectRecord {
  id: number
  name: string
  description: string | null
  skills_used: string[]
  github_url: string | null
  status: 'planning' | 'in_progress' | 'completed'
  linked_node_id: string | null
  reflection: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface InterviewRecord {
  id: number
  company: string
  position: string
  round: string
  content_summary: string
  self_rating: 'good' | 'medium' | 'bad'
  result: 'passed' | 'failed' | 'pending'
  reflection: string | null
  ai_analysis: {
    strengths: string[]
    weaknesses: string[]
    action_items: string[]
    overall: string
  } | null
  application_id: number | null
  interview_at: string | null
  created_at: string
}

export interface MonthlySummary {
  month: string
  projects: number
  interviews: number
  learnings: number
  total_events: number
  readiness_start: number | null
  readiness_current: number | null
  readiness_delta: number | null
}

/* ── Timeline ── */

export const getTimeline = (params?: { event_type?: string; limit?: number; offset?: number }) =>
  rawFetch<{ events: GrowthEvent[]; total: number }>(
    `${BASE}/timeline${params ? '?' + new URLSearchParams(Object.entries(params).filter(([, v]) => v != null).map(([k, v]) => [k, String(v)])).toString() : ''}`
  )

export const getMonthlySummary = () =>
  rawFetch<MonthlySummary>(`${BASE}/summary`)

/* ── Projects ── */

export const listProjects = () =>
  rawFetch<{ projects: ProjectRecord[] }>(`${BASE}/projects`)

export const createProject = (data: {
  name: string
  description?: string
  skills_used?: string[]
  github_url?: string
  status?: string
  linked_node_id?: string
  reflection?: string
  started_at?: string
}) =>
  rawFetch<ProjectRecord>(`${BASE}/projects`, {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const updateProject = (id: number, data: {
  name?: string
  description?: string
  skills_used?: string[]
  github_url?: string
  status?: string
  linked_node_id?: string
  reflection?: string
}) =>
  rawFetch<ProjectRecord>(`${BASE}/projects/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })

export const deleteProject = (id: number) =>
  rawFetch<void>(`${BASE}/projects/${id}`, { method: 'DELETE' })

/* ── Interviews ── */

export const listInterviews = () =>
  rawFetch<{ interviews: InterviewRecord[] }>(`${BASE}/interviews`)

export const createInterview = (data: {
  company: string
  position?: string
  round?: string
  content_summary: string
  self_rating?: string
  result?: string
  reflection?: string
  interview_at?: string
  application_id?: number
}) =>
  rawFetch<InterviewRecord>(`${BASE}/interviews`, {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const updateInterview = (id: number, data: {
  result?: string
  reflection?: string
  self_rating?: string
}) =>
  rawFetch<InterviewRecord>(`${BASE}/interviews/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })

export const analyzeInterview = (id: number) =>
  rawFetch<InterviewRecord>(`${BASE}/interviews/${id}/analyze`, { method: 'POST' })

/* ── Project Logs ── */

export interface ProjectLogEntry {
  id: number
  content: string
  log_type: 'progress' | 'note'
  created_at: string
}

export const listProjectLogs = (projectId: number) =>
  rawFetch<{ logs: ProjectLogEntry[] }>(`${BASE}/projects/${projectId}/logs`)

export const createProjectLog = (projectId: number, content: string, log_type: 'progress' | 'note' = 'progress') =>
  rawFetch<ProjectLogEntry>(`${BASE}/projects/${projectId}/logs`, {
    method: 'POST',
    body: JSON.stringify({ content, log_type }),
  })

export const deleteProjectLog = (projectId: number, logId: number) =>
  rawFetch<void>(`${BASE}/projects/${projectId}/logs/${logId}`, { method: 'DELETE' })

export const deleteInterview = (id: number) =>
  rawFetch<void>(`${BASE}/interviews/${id}`, { method: 'DELETE' })
