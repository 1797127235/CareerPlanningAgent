import { rawFetch } from '@/api/client'

export interface Question {
  id: string
  type: 'technical' | 'behavioral' | 'scenario'
  question: string
  focus_area: string
  difficulty: 'easy' | 'medium' | 'hard'
  follow_ups?: string[]
}

export interface FollowUpTurn {
  question: string
  answer: string
  source?: string
}

export interface Answer {
  question_id: string
  answer: string
  follow_ups: FollowUpTurn[]
}

export interface PerQuestionEval {
  question_id: string
  score: number
  strengths: string[]
  improvements: string[]
  suggested_answer: string
  follow_up_comment?: string
}

export interface Evaluation {
  overall_score: number
  overall_comment: string
  per_question: PerQuestionEval[]
  skill_gaps: string[]
  tips: string[]
}

export interface InterviewHistoryItem {
  id: number
  target_role: string
  status: string
  score: number | null
  created_at: string
}

export interface InterviewSession {
  id: number
  target_role: string
  status: string
  questions: Question[]
  answers?: Answer[]
  evaluation?: Record<string, unknown> | null
}

export async function startInterview(body: {
  target_role: string
  jd_text: string
  question_count: number
  type_distribution: Record<string, number>
}): Promise<{ id: number; questions: Question[] }> {
  return rawFetch('/interview/start', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function submitInterview(
  interviewId: number,
  body: { answers: Answer[] }
): Promise<Record<string, unknown>> {
  return rawFetch(`/interview/${interviewId}/submit`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function generateFollowUp(
  interviewId: number,
  body: { question_id: string; answer: string; follow_ups: FollowUpTurn[] }
): Promise<{ follow_up?: string; round: number; max_rounds: number; done: boolean }> {
  return rawFetch(`/interview/${interviewId}/follow-up`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function fetchInterviewHistory(): Promise<InterviewHistoryItem[]> {
  return rawFetch('/interview/history')
}

export async function fetchInterviewSession(id: number): Promise<InterviewSession> {
  return rawFetch(`/interview/${id}`)
}

export async function deleteInterview(id: number): Promise<void> {
  return rawFetch(`/interview/${id}`, { method: 'DELETE' })
}
