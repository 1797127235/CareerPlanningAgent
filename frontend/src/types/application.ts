export type ApplicationStatus =
  | 'pending' | 'applied' | 'screening' | 'scheduled'
  | 'interviewed' | 'debriefed' | 'offer' | 'rejected' | 'withdrawn'

export interface QAItem {
  question: string
  answer: string
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
}

export interface CreateApplicationRequest {
  jd_diagnosis_id?: number
  company?: string
  position?: string
  job_url?: string
  notes?: string
}
