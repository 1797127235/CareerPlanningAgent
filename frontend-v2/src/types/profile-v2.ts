export interface V2Skill {
  name: string
  level: 'beginner' | 'familiar' | 'intermediate' | 'advanced'
}

export interface V2Education {
  degree: string
  major: string
  school: string
  graduation_year?: number
  duration: string
}

export interface V2Internship {
  company: string
  role: string
  duration: string
  tech_stack: string[]
  highlights: string
}

export interface V2Project {
  name: string
  description: string
  tech_stack: string[]
  duration: string
  highlights: string
}

export interface V2ProfileData {
  name: string
  job_target_text: string
  domain_hint: string
  education: V2Education[]
  skills: V2Skill[]
  projects: V2Project[]
  internships: V2Internship[]
  awards: string[]
  certificates: string[]
  raw_text: string
}

export interface V2ResumeDocument {
  filename: string
  content_type: string | null
  raw_text: string
  text_format: 'plain' | 'markdown'
  extraction_method: string
  ocr_used: boolean
  file_hash: string
  warnings: string[]
}

export interface V2ParseMeta {
  llm_model: string
  evidence_sources: string[]
  json_repaired: boolean
  retry_count: number
  quality_score: number
  quality_checks: Record<string, boolean>
  warnings: string[]
}

export interface V2ParsePreviewResponse {
  profile: V2ProfileData
  document: V2ResumeDocument
  meta: V2ParseMeta
}

export interface V2SaveProfileResponse {
  profile_id: number
  parse_id: number
  message: string
}
