/* ── Shared profile types ── */

export interface Skill {
  name: string
  level: 'expert' | 'proficient' | 'familiar' | 'beginner' | 'advanced' | 'intermediate'
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

export interface Internship {
  company: string
  role: string
  duration?: string
  tech_stack?: string[]
  highlights?: string
  tier?: string
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
    internships?: Internship[]
    certificates?: string[]
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

export interface ManualProfilePayload {
  name: string
  education: { degree: string; major: string; school: string }
  experience_years: number
  job_target: string
  skills: Skill[]
  knowledge_areas: string[]
  projects: Array<string | Record<string, unknown>>
  internships: Internship[]
  certificates: string[]
  awards: string[]
}
