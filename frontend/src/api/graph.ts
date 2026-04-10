import { rawFetch } from '@/api/client'
import type {
  GraphMapResponse,
  EscapeRoutesResponse,
  SearchResponse,
  LearningResponse,
  LearningSummary,
} from '@/types/graph'

export async function fetchGraphMap(): Promise<GraphMapResponse> {
  return rawFetch<GraphMapResponse>('/graph/map')
}

export async function fetchEscapeRoutes(nodeId: string): Promise<EscapeRoutesResponse> {
  return rawFetch<EscapeRoutesResponse>(`/graph/escape-routes?node_id=${encodeURIComponent(nodeId)}`)
}

export async function searchGraphNodes(q: string): Promise<SearchResponse> {
  return rawFetch<SearchResponse>(`/graph/search?q=${encodeURIComponent(q)}`)
}

export async function fetchNodeIntro(nodeId: string): Promise<{ node_id: string; intro: string }> {
  return rawFetch(`/graph/node/${encodeURIComponent(nodeId)}/intro`)
}

export interface SetCareerGoalPayload {
  profile_id: number
  target_node_id: string
  target_label: string
  target_zone: string
  gap_skills: string[]
  estimated_hours: number
  safety_gain: number
  salary_p50: number
}

export async function setCareerGoal(
  payload: SetCareerGoalPayload,
): Promise<{ ok: boolean; target_label: string; target_zone: string }> {
  return rawFetch('/graph/career-goal', {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

// ── Multi-goal CRUD ──────────────────────────────────────────────────────────

export interface AddCareerGoalPayload {
  target_node_id: string
  target_label: string
  target_zone: string
  gap_skills: string[]
  estimated_hours: number
  safety_gain: number
  salary_p50: number
  set_as_primary?: boolean
}

export async function addCareerGoal(
  payload: AddCareerGoalPayload,
): Promise<{ ok: boolean; goal_id: number; target_label: string }> {
  return rawFetch('/graph/career-goals', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

// ── Learning resources ────────────────────────────────────────────────────

export async function fetchNodeLearning(
  nodeId: string,
  opts?: { type?: string; limit?: number; offset?: number },
): Promise<LearningResponse> {
  const params = new URLSearchParams()
  if (opts?.type) params.set('resource_type', opts.type)
  if (opts?.limit) params.set('limit', String(opts.limit))
  if (opts?.offset) params.set('offset', String(opts.offset))
  const qs = params.toString()
  return rawFetch<LearningResponse>(`/graph/node/${encodeURIComponent(nodeId)}/learning${qs ? `?${qs}` : ''}`)
}

export async function fetchNodeLearningSummary(nodeId: string): Promise<LearningSummary> {
  return rawFetch<LearningSummary>(`/graph/node/${encodeURIComponent(nodeId)}/learning/summary`)
}
