export type Category = 'learning' | 'interview' | 'project' | null

export interface InterviewQA {
  q: string
  a: string
}

export interface InterviewData {
  company: string
  position: string
  round: string
  questions: InterviewQA[]
  self_rating: 'good' | 'medium' | 'bad'
  result: 'passed' | 'failed' | 'pending'
  reflection?: string
}

export interface ProjectData {
  name: string
  description?: string
  skills_used: string[]
  github_url?: string
  status: 'planning' | 'in_progress' | 'completed'
}

export interface AiSuggestion {
  text: string
  category?: Category
}

export interface GrowthEntry {
  id: number
  content: string
  category: Category
  tags: string[]
  structured_data: InterviewData | ProjectData | null
  is_plan: boolean
  status: 'done' | 'pending' | 'dropped'
  due_type: 'daily' | 'weekly' | 'monthly' | 'custom' | null
  due_at: string | null
  completed_at: string | null
  created_at: string
  ai_suggestions: AiSuggestion[] | null
}
