import { rawFetch } from '@/api/client'
import type { AnalyzeRequest, EvaluationResult, PracticeRecord } from '@/types/practice'

export async function analyzeAnswer(req: AnalyzeRequest): Promise<EvaluationResult> {
  return rawFetch<EvaluationResult>('/practice/analyze', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export async function fetchPracticeHistory(): Promise<PracticeRecord[]> {
  return rawFetch<PracticeRecord[]>('/practice/history')
}

export async function deletePracticeRecord(id: number): Promise<void> {
  await rawFetch<{ ok: boolean }>(`/practice/reviews/${id}`, {
    method: 'DELETE',
  })
}

export interface QuestionItem {
  id: number
  question: string
  skill_tag: string
  question_type: string
  question_category?: string
  difficulty: string
  answer_key?: string | null
}

export async function fetchQuestions(skillTag?: string): Promise<QuestionItem[]> {
  const params = skillTag ? `?skill_tag=${encodeURIComponent(skillTag)}` : ''
  return rawFetch<QuestionItem[]>(`/practice/questions${params}`)
}
