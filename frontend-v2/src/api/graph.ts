import { rawFetch } from '@/api/client'
import type {
  GraphMapResponse,
  EscapeRoutesResponse,
  SearchResponse,
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

export async function patchCareerGoalGaps(
  gap_skills: string[],
  source: string,
): Promise<{ ok: boolean; gap_count: number; target_label: string }> {
  return rawFetch('/graph/career-goal/gaps', {
    method: 'PATCH',
    body: JSON.stringify({ gap_skills, source }),
  })
}

