import { rawFetch } from '@/api/client'

export interface Recommendation {
  role_id: string
  label: string
  affinity_pct: number
  matched_skills: string[]
  gap_skills: string[]
  gap_hours: number
  zone: string
  salary_p50: number
  reason: string
  channel?: 'entry' | 'growth' | 'explore'
  career_level?: number
  replacement_pressure?: number
  human_ai_leverage?: number
}

export interface RecommendationsResponse {
  recommendations: Recommendation[]
  user_skill_count: number
}

export interface MatchDetail {
  role_id: string
  label?: string
  mastered: Array<{ module: string; reason: string }>
  gaps: Array<{ module: string; reason: string; priority: string }>
  mastered_count: number
  gap_count: number
  coverage_pct: number
  failed?: boolean
}

export async function fetchRecommendations(topK = 5): Promise<RecommendationsResponse> {
  return rawFetch<RecommendationsResponse>(`/recommendations?top_k=${topK}`)
}

export async function fetchMatchDetail(roleId: string): Promise<MatchDetail> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 60_000)
  try {
    return await rawFetch(`/recommendations/match-analysis/${roleId}`, { signal: controller.signal })
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') {
      throw new Error('分析超时，请重试')
    }
    throw e
  } finally {
    clearTimeout(timer)
  }
}
