import { rawFetch } from '@/api/client'
import type { DashboardStats } from '@/types/dashboard'

export async function fetchDashboardStats(profileId: number): Promise<DashboardStats> {
  return rawFetch<DashboardStats>(`/dashboard/stats?profile_id=${profileId}`)
}
