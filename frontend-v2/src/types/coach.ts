export interface GapSkill {
  skill: string
  priority: string
  match_delta: number
}

export interface StructuredJdDetail {
  _structured?: boolean
  match_score?: number
  matched_skills?: string[]
  gap_skills?: GapSkill[]
  jd_title?: string
  company?: string
  job_url?: string
  raw_text?: string
}

export interface CoachResultDetail {
  id: number
  result_type: string
  title: string
  summary: string
  detail: StructuredJdDetail & Record<string, unknown>
  metadata: Record<string, unknown>
  created_at: string
}

export interface CoachResultListItem {
  id: number
  result_type: string
  title: string
  summary: string
  metadata: Record<string, unknown>
  created_at: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatRequestBody {
  message: string
  context?: ChatMessage[]
}
