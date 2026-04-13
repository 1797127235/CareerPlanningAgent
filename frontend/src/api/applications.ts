import type { JobApplication, CreateApplicationRequest, ApplicationStatus, QAItem } from '@/types/application'

const BASE = '/api/applications'

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token')
  const res = await fetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    const error = new Error(
      typeof err.detail === 'string' ? err.detail : `请求失败 (${res.status})`
    ) as Error & { status: number; detail: unknown }
    error.status = res.status
    error.detail = err.detail
    throw error
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const listApplications = (): Promise<JobApplication[]> =>
  req(BASE)

export const createApplication = (data: CreateApplicationRequest): Promise<JobApplication> =>
  req(BASE, { method: 'POST', body: JSON.stringify(data) })

export const updateApplicationStatus = (id: number, status: ApplicationStatus): Promise<JobApplication> =>
  req(`${BASE}/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status }) })

export const setInterviewTime = (id: number, interview_at: string): Promise<JobApplication> =>
  req(`${BASE}/${id}/interview-time`, { method: 'PATCH', body: JSON.stringify({ interview_at }) })

export const updateNotes = (id: number, notes: string): Promise<void> =>
  req(`${BASE}/${id}/notes`, { method: 'PATCH', body: JSON.stringify({ notes }) })

export const deleteApplication = (id: number): Promise<void> =>
  req(`${BASE}/${id}`, { method: 'DELETE' })

export const updateReflection = (id: number, reflection: string): Promise<void> =>
  req(`${BASE}/${id}/reflection`, { method: 'PATCH', body: JSON.stringify({ reflection }) })

export const submitDebrief = (id: number, qa_list: QAItem[]) =>
  req(`${BASE}/${id}/debrief`, { method: 'POST', body: JSON.stringify({ qa_list }) })
