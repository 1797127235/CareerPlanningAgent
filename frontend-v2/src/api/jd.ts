import { rawFetch } from '@/api/client'
import type { DiagnoseRequest, DiagnoseResult, CoachInsight } from '@/types/jd'

export async function diagnoseJd(req: DiagnoseRequest): Promise<DiagnoseResult> {
  return rawFetch<DiagnoseResult>('/jd/diagnose', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export interface GraphContext {
  node_id: string
  label: string
  zone: 'leverage' | 'transition' | 'caution' | 'critical'
  replacement_pressure: number
  human_ai_leverage: number
  escape_routes: Array<{
    target_label: string
    target_zone: string
    tag: string
    gap_skills: string[]
    estimated_hours: number
  }>
}

export interface JDDiagnosisDetail {
  id: number
  jd_title: string
  jd_text: string
  match_score: number
  created_at: string
  dimensions?: Record<string, { score: number; weight: number; detail?: string }>
  matched_skills?: Array<{ skill: string; level?: string }> | string[]
  gap_skills?: Array<{ skill: string; priority?: string }> | string[]
  extracted_skills?: string[]
  resume_tips?: string[]
  graph_context?: GraphContext | null
  coach_insight?: CoachInsight | null
}

export async function getJDDiagnosis(id: number): Promise<JDDiagnosisDetail> {
  return rawFetch(`/jd/${id}`)
}

export async function listJDDiagnoses(): Promise<
  Array<{
    id: number
    profile_id: number
    jd_title: string
    match_score: number
    created_at: string
    dimensions?: Record<string, { score: number; weight: number; detail?: string }>
    matched_skills?: Array<{ skill: string; level?: string }> | string[]
    gap_skills?: Array<{ skill: string; priority?: string }> | string[]
    extracted_skills?: string[]
    resume_tips?: string[]
    graph_context?: GraphContext | null
  }>
> {
  return rawFetch('/jd/history')
}
