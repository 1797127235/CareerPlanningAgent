export interface DiagnoseRequest {
  jd_text: string
  profile_id: number
  jd_title?: string
}

export interface GapSkill {
  skill: string
  match_delta: number
  priority: 'high' | 'medium'
}

export interface DimensionScore {
  score: number
  label: string
  detail: string
}

export type DimensionKey = 'basic' | 'skills' | 'qualities' | 'potential'

export type Dimensions = Record<DimensionKey, DimensionScore>

export interface GraphContext {
  node_id: string
  label: string
  zone: string
  replacement_pressure: number
  human_ai_leverage: number
  escape_routes: Array<{
    target_label: string
    target_zone: string
    tag: string
    gap_skills: string[]
    estimated_hours: number
  }>
}

export interface CoachInsight {
  type: string
  title: string
  insight: string
  evidence: string[]
  cta: {
    text: string
    action: 'open_chat' | 'navigate' | 'execute'
    target?: string
    prompt?: string
  }
  secondary_cta?: {
    text: string
    action: 'open_chat' | 'navigate' | 'execute'
    target?: string
    prompt?: string
  }
}

export interface DiagnoseResult {
  id: number
  match_score: number
  dimensions?: Dimensions
  matched_skills: string[]
  gap_skills: GapSkill[]
  extracted_skills: string[]
  resume_tips?: string[]
  graph_context?: GraphContext | null
  coach_insight?: CoachInsight | null
}

export interface DiagnosisRecord {
  id: number
  profile_id: number
  jd_title: string
  match_score: number
  created_at: string
  dimensions?: Dimensions
  matched_skills?: string[]
  gap_skills?: GapSkill[]
  extracted_skills?: string[]
  resume_tips?: string[]
}
