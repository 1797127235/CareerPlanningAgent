import { apiFetch, rawFetch, apiUpload } from '@/api/client'
import type { ProfileData } from '@/types/profile'

/** Fetch the single profile for the current user */
export async function fetchProfile(): Promise<ProfileData | null> {
  const res = await apiFetch<ProfileData>('/profiles')
  return res.success && res.data ? res.data : null
}

export interface UpdateProfilePayload {
  name?: string
  profile?: Record<string, unknown>
  quality?: Record<string, unknown> | null
  merge?: boolean
}

/** Update the current profile */
export async function updateProfile(payload: UpdateProfilePayload): Promise<void> {
  await apiFetch('/profiles', {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

/** Set profile display name */
export async function setProfileName(name: string): Promise<void> {
  await apiFetch('/profiles/name', {
    method: 'PATCH',
    body: JSON.stringify({ name: name.trim() }),
  })
}

/** Refine a project by matching original text */
export async function refineProject(originalText: string, newDescription: string): Promise<void> {
  await apiFetch('/profiles/me/projects/refine', {
    method: 'PATCH',
    body: JSON.stringify({ original_text: originalText, new_description: newDescription }),
  })
}

/** Reset profile to empty */
export async function resetProfile(): Promise<void> {
  await apiFetch('/profiles', { method: 'DELETE' })
}

/** Re-run LLM extraction on stored raw_text */
export async function reparseProfile(): Promise<void> {
  await apiFetch('/profiles/reparse', { method: 'POST' })
}

// ── SJT v2 types ─────────────────────────────────────────────

export interface SjtQuestion {
  id: string
  dimension: string
  scenario: string
  options: Array<{ id: string; text: string }>
}

export interface SjtAnswer {
  question_id: string
  best: string
  worst: string
}

export interface SjtGenerateResult {
  session_id: string
  questions: SjtQuestion[]
}

export interface SjtDimensionResult {
  key: string
  level: string
  advice: string
}

export interface SjtSubmitResult {
  dimensions: SjtDimensionResult[]
  overall_level: string
}

export interface SjtProgress {
  session_id: string
  questions: SjtQuestion[]
  answers: SjtAnswer[]
  current_idx: number
}

export async function generateSjt(): Promise<SjtGenerateResult> {
  const res = await rawFetch('/profiles/sjt/generate', { method: 'POST' })
  return res.data
}

export async function getSjtProgress(): Promise<SjtProgress | null> {
  const res = await rawFetch('/profiles/sjt/progress')
  return res.data
}

export async function saveSjtProgress(sessionId: string, answers: SjtAnswer[], currentIdx: number): Promise<void> {
  await rawFetch('/profiles/sjt/save', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, answers, current_idx: currentIdx }),
  })
}

export async function submitSjt(sessionId: string, answers: SjtAnswer[]): Promise<SjtSubmitResult> {
  const res = await rawFetch('/profiles/sjt/submit', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, answers }),
  })
  return res.data
}

// ── Project CRUD ──

export interface ProjectPayload {
  name: string
  description?: string
  tech_stack?: string[]
}

export async function addProject(project: ProjectPayload): Promise<void> {
  await apiFetch('/profiles/projects', {
    method: 'POST',
    body: JSON.stringify(project),
  })
}

export async function updateProject(index: number, project: ProjectPayload): Promise<void> {
  await apiFetch(`/profiles/projects/${index}`, {
    method: 'PATCH',
    body: JSON.stringify(project),
  })
}

export async function deleteProject(index: number): Promise<void> {
  await apiFetch(`/profiles/projects/${index}`, {
    method: 'DELETE',
  })
}
