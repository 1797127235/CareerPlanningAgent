export interface AnalyzeRequest {
  question: string
  answer: string
  target_job?: string
  profile_id?: number
}

export interface Strength {
  point: string
  detail: string
}

export interface Weakness {
  point: string
  suggestion: string
}

export interface Dimension {
  name: string
  score: number
  comment: string
}

export interface EvaluationResult {
  strengths: Strength[]
  weaknesses: Weakness[]
  overall_feedback: string
  score: number
  dimensions?: Dimension[]
}

export interface PracticeRecord {
  id: number
  profile_id: number
  target_job: string
  question_text: string
  score: number
  created_at: string
}
