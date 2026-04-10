import { useState, useEffect } from 'react'
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
  const [data, setData] = useState<HeatmapData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    rawFetch<HeatmapData>(`/dashboard/activity-heatmap?weeks=${weeks}`)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [weeks])

  return { data, loading }
}
