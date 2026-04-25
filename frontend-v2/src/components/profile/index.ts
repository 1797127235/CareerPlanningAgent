import type { Internship, Skill } from '@/types/profile'

export interface ManualProfilePayload {
  name: string
  education: {
    degree: string
    major: string
    school: string
  }
  experience_years: number
  job_target: string
  skills: Skill[]
  knowledge_areas: string[]
  projects: string[]
  internships: Internship[]
  certificates: string[]
  awards: string[]
}
