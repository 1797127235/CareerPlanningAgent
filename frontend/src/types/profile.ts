/* ── Shared profile types ── */

export interface Skill {
  name: string
  level: 'expert' | 'proficient' | 'familiar' | 'beginner'
}

export interface CompetencyDimension {
  key?: string
  label?: string
  name?: string
  score: number
}

export interface GraphPosition {
  from_node_id: string
  from_node_label: string
  target_node_id: string
  target_label: string
  target_zone: string
  gap_skills?: string[]
  total_hours?: number
  safety_gain?: number
  salary_p50?: number
}

export interface CareerGoal {
  id: number
  target_node_id: string
  target_label: string
  target_zone: string
  from_node_id: string
  from_node_label: string
  gap_skills: string[]
  total_hours: number
  safety_gain: number
  salary_p50: number
  is_primary: boolean
  set_at: string | null
}

export interface Education {
  degree?: string
  major?: string
  school?: string
}

export interface SoftSkillEntry {
  score: number
  level?: 'high' | 'medium' | 'low'
  evidence?: string
}

export interface ProfileData {
  id: number
  name: string
  source: string
  created_at: string
  updated_at: string
  profile: {
    skills?: Skill[]
    knowledge_areas?: string[]
    education?: Education
    experience_years?: number
    projects?: string[]
    soft_skills?: Record<string, SoftSkillEntry | number>
    [key: string]: unknown
  }
  quality: {
    completeness?: number
    competitiveness?: number
    confidence?: number
    overall_score?: number
    industry_avg?: number
    dimensions?: CompetencyDimension[]
    [key: string]: unknown
  }
  graph_position?: GraphPosition
  career_goals?: CareerGoal[]
}

export interface CheckItem {
  label: string
  done: boolean
}
