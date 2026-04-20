import { apiFetch } from '@/api/client'
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
  const res = await apiFetch<SjtGenerateResult>('/profiles/sjt/generate', {
    method: 'POST',
  })
  if (!res.success || !res.data) throw new Error('题目生成失败：返回数据为空')
  return res.data
}

export async function submitSjt(
  sessionId: string,
  answers: SjtAnswer[],
): Promise<SjtSubmitResult> {
  const res = await apiFetch<SjtSubmitResult>('/profiles/sjt/submit', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, answers }),
  })
  if (!res.success || !res.data) throw new Error('提交失败')
  return res.data
}
