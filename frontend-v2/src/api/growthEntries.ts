import { rawFetch } from './client'
import type {
  InterviewQA,
  InterviewData,
  ProjectData,
  AiSuggestion,
  GrowthEntry,
} from '@/components/growth-log/mockData'

const BASE = '/growth-log'

export type { InterviewQA, InterviewData, ProjectData, AiSuggestion, GrowthEntry }

export const listEntries = (params?: { status?: string; category?: string; tag?: string }) => {
  const q = new URLSearchParams()
  if (params?.status) q.set('status', params.status)
  if (params?.category) q.set('category', params.category)
  if (params?.tag) q.set('tag', params.tag)
  const qs = q.toString()
  return rawFetch<{ entries: GrowthEntry[] }>(`${BASE}/entries${qs ? '?' + qs : ''}`)
}

export const createEntry = (data: Partial<GrowthEntry>) =>
  rawFetch<GrowthEntry>(`${BASE}/entries`, { method: 'POST', body: JSON.stringify(data) })

export const updateEntry = (id: number, patch: Partial<GrowthEntry>) =>
  rawFetch<GrowthEntry>(`${BASE}/entries/${id}`, { method: 'PATCH', body: JSON.stringify(patch) })

export const deleteEntry = (id: number) =>
  rawFetch<void>(`${BASE}/entries/${id}`, { method: 'DELETE' })

export const aiSuggest = (id: number) =>
  rawFetch<{ suggestions: AiSuggestion[] }>(`${BASE}/entries/${id}/ai-suggest`, { method: 'POST' })
