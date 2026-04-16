import { rawFetch } from './client'

export type CareerStage = 'exploring' | 'focusing' | 'job_hunting' | 'sprinting'

export async function fetchCareerStage(): Promise<{ stage: CareerStage }> {
  return rawFetch<{ stage: CareerStage }>('/auth/me/stage')
}
