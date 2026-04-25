import { rawFetch } from '@/api/client'

const BASE = '/growth-log'

/* ── Types ── */

export interface ProjectRecord {
  id: number
  name: string
  description: string | null
  skills_used: string[]
  gap_skill_links: string[]
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

/* ── Goal Journey ── */

export interface StageEvent {
  id: number
  trigger: 'initial' | 'stage_complete' | 'deep_reeval'
  stage_completed: number | null
  readiness_score: number
  created_at: string
}

export interface GoalJourney {
  has_goal: boolean
  goal?: {
    id: number
    target_node_id: string
    target_label: string
    set_at: string
  }
  stage_events?: StageEvent[]
  projects_under_goal?: {
    id: number
    name: string
    status: string
    created_at: string
  }[]
  applications_under_goal?: {
    id: number
    company: string
    position: string
    status: string
    created_at: string
  }[]
}

export interface GoalHistoryItem {
  id: number
  target_node_id: string
  target_label: string
  is_active: boolean
  is_primary: boolean
  set_at: string
  cleared_at: string | null
  duration_days: number
}

export const getGoalJourney = () =>
  rawFetch<GoalJourney>(`${BASE}/journey`)

export const getGoalHistory = () =>
  rawFetch<{ goals: GoalHistoryItem[] }>(`${BASE}/goal-history`)

/* ── Skills Harvest ── */

export interface SkillTouched {
  name: string
  first_seen_at: string
  use_count?: number
}

export interface SkillsHarvestData {
  has_records: boolean
  month_label: string
  monthly_record_count: number
  newly_touched_skills: SkillTouched[]
  all_touched_skills: SkillTouched[]
}

export const getSkillsHarvest = () =>
  rawFetch<SkillsHarvestData>(`${BASE}/skills-harvest`)

/* ── Activity Pulse ── */

export interface WeeklyActivity {
  week_label: string
  iso_week: string
  projects: number
  applications: number
  interviews: number
}

export interface ActivityPulseData {
  current_streak_weeks: number
  total_records: number
  weeks: WeeklyActivity[]
}

export const getActivityPulse = () =>
  rawFetch<ActivityPulseData>(`${BASE}/activity-pulse`)

/* ── Projects ── */

export const listProjects = () =>
  rawFetch<{ projects: ProjectRecord[] }>(`${BASE}/projects`)

export const createProject = (data: {
  name: string
  description?: string
  skills_used?: string[]
  gap_skill_links?: string[]
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
  gap_skill_links?: string[]
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

export const createProjectLog = (projectId: number, data: {
  content: string
  reflection?: string
  task_status?: 'done' | 'in_progress' | 'blocked'
  log_type?: 'progress' | 'note'
}) =>
  rawFetch<ProjectLogEntry>(`${BASE}/projects/${projectId}/logs`, {
    method: 'POST',
    body: JSON.stringify({ log_type: 'progress', ...data }),
  })

export const deleteProjectLog = (projectId: number, logId: number) =>
  rawFetch<void>(`${BASE}/projects/${projectId}/logs/${logId}`, { method: 'DELETE' })

export const deleteInterview = (id: number) =>
  rawFetch<void>(`${BASE}/interviews/${id}`, { method: 'DELETE' })

/* ── Project Graph ── */

export interface GraphData {
  nodes: Record<string, unknown>[]
  edges: Record<string, unknown>[]
}

export const getProjectGraph = (id: number) =>
  rawFetch<GraphData>(`${BASE}/projects/${id}/graph`)

export const saveProjectGraph = (id: number, data: GraphData) =>
  rawFetch<{ ok: boolean }>(`${BASE}/projects/${id}/graph`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
