import { useQuery } from '@tanstack/react-query'
import { rawFetch } from '@/api/client'

interface HeatmapDay {
  date: string
  count: number
  activities: string[]
}

interface HeatmapData {
  days: HeatmapDay[]
  streak: number
}

export function useActivityHeatmap(weeks = 16) {
  return useQuery<HeatmapData>({
    queryKey: ['activity-heatmap', weeks],
    queryFn: () => rawFetch<HeatmapData>(`/dashboard/activity-heatmap?weeks=${weeks}`),
    staleTime: 60_000,
  })
}
