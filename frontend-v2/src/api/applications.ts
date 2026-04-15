import { rawFetch } from '@/api/client'
import type { JobApplication, CreateApplicationRequest, ApplicationStatus, QAItem } from '@/types/application'

const BASE = '/api/applications'

export const listApplications = (): Promise<JobApplication[]> =>
  rawFetch<JobApplication[]>(BASE)

export const createApplication = (data: CreateApplicationRequest): Promise<JobApplication> =>
  rawFetch<JobApplication>(BASE, { method: 'POST', body: JSON.stringify(data) })

export const updateApplicationStatus = (id: number, status: ApplicationStatus): Promise<JobApplication> =>
  rawFetch<JobApplication>(`${BASE}/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status }) })

export const setInterviewTime = (id: number, interview_at: string): Promise<JobApplication> =>
  rawFetch<JobApplication>(`${BASE}/${id}/interview-time`, { method: 'PATCH', body: JSON.stringify({ interview_at }) })

export const updateNotes = (id: number, notes: string): Promise<void> =>
  rawFetch<void>(`${BASE}/${id}/notes`, { method: 'PATCH', body: JSON.stringify({ notes }) })

export const deleteApplication = (id: number): Promise<void> =>
  rawFetch<void>(`${BASE}/${id}`, { method: 'DELETE' })

export const updateReflection = (id: number, reflection: string): Promise<void> =>
  rawFetch<void>(`${BASE}/${id}/reflection`, { method: 'PATCH', body: JSON.stringify({ reflection }) })

export const submitDebrief = (id: number, qa_list: QAItem[]) =>
  rawFetch<unknown>(`${BASE}/${id}/debrief`, { method: 'POST', body: JSON.stringify({ qa_list }) })
