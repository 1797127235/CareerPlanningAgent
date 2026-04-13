export type ApplicationStatus =
  | 'pending' | 'applied' | 'screening' | 'scheduled'
  | 'interviewed' | 'debriefed' | 'offer' | 'rejected' | 'withdrawn'

export interface QAItem {
  question: string
  answer: string
}

export interface DebriefQuestionReview {
  question: string
  your_answer: string
  score: number
  strengths: string[]
  weaknesses: string[]
  suggested_answer: string
  skill_tags: string[]
}

export interface DebriefReport {
  overall_score: number
  summary: string
  question_reviews: DebriefQuestionReview[]
  gap_skills: Array<{ skill: string; priority: string; advice: string }>
  overall_tips: string[]
}

export interface ApplicationDebrief {
  id: number
  raw_input: QAItem[]
  report: DebriefReport | null
  created_at: string
}

export interface JdDiagnosisSummary {
  match_score: number
  gap_skills: Array<{ skill: string; gap_level?: string }> | string[]
  matched_skills: string[]
}

export interface MockSessionSummary {
  id: number
  overall_score: number
  status: string
  created_at: string
}

export interface JobApplication {
  id: number
  jd_diagnosis_id: number | null
  jd_title: string | null
  company: string | null
  position: string | null
  job_url: string | null
  status: ApplicationStatus
  applied_at: string | null
  interview_at: string | null
  completed_at: string | null
  notes: string | null
  reflection: string | null
  reminder_sent: boolean
  created_at: string
  updated_at: string
  debrief: ApplicationDebrief | null
  jd_diagnosis: JdDiagnosisSummary | null
  mock_sessions: MockSessionSummary[]
}

export interface CreateApplicationRequest {
  jd_diagnosis_id?: number
  company?: string
  position?: string
  job_url?: string
  notes?: string
}
