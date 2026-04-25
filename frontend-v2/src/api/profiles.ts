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

/** Parse resume file (returns preview, does NOT save) */
export async function parseResume(file: File): Promise<{ profile: Record<string, unknown>; quality: Record<string, unknown> }> {
  const res = await apiUpload<{ profile: Record<string, unknown>; quality: Record<string, unknown> }>('/profiles/parse-resume', file)
  if (!res.success || !res.data) throw new Error(res.message || '简历解析失败')
  return res.data
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

/** Update project by index (legacy) */
export async function updateProject(projIndex: number, description: string): Promise<void> {
  await apiFetch(`/profiles/me/projects/${projIndex}`, {
    method: 'PATCH',
    body: JSON.stringify({ description }),
  })
}

/** Reset profile to empty */
export async function resetProfile(): Promise<void> {
  await apiFetch('/profiles', { method: 'DELETE' })
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

export async function generateSjt(): Promise<SjtGenerateResult> {
  const res = await rawFetch('/profiles/sjt/generate', { method: 'POST' })
  return res.data
}

export async function submitSjt(sessionId: string, answers: SjtAnswer[]): Promise<SjtSubmitResult> {
  const res = await rawFetch('/profiles/sjt/submit', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, answers }),
  })
  return res.data
}
