import { rawFetch } from '@/api/client'
import type { DiagnoseRequest, CoachInsight } from '@/types/jd'

/* ── v2 API paths (backend2) ── */
const V2 = '/v2/opportunities'

export async function diagnoseJd(req: DiagnoseRequest): Promise<JDDiagnosisDetail> {
  const res = await rawFetch<V2DiagnosisResponse>(`${V2}/evaluate`, {
    method: 'POST',
    body: JSON.stringify({ jd_text: req.jd_text, jd_title: req.jd_title ?? '' }),
  })
  return adaptV2Response(res)
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
  const res = await rawFetch<V2DiagnosisResponse>(`${V2}/evaluations/${id}`)
  return adaptV2Response(res)
}

export async function listJDDiagnoses(): Promise<JDDiagnosisDetail[]> {
  const items = await rawFetch<V2ListItem[]>(`${V2}/evaluations`)
  return items.map((item) => ({
    id: item.id,
    jd_title: item.jd_title,
    jd_text: '',
    match_score: item.match_score,
    created_at: item.created_at,
    matched_skills: [],
    gap_skills: [],
    extracted_skills: [],
    resume_tips: [],
    graph_context: null,
    coach_insight: null,
  }))
}

/* ── v2 response shapes (backend2/opportunity schema) ── */

interface V2GapSkill {
  skill: string
  priority: 'high' | 'medium' | 'low'
  reason: string
  evidence: string
  action_hint: string
}

interface V2JDExtract {
  title: string
  company: string
  responsibilities: string[]
  required_skills: string[]
  preferred_skills: string[]
  basic_requirements: {
    education: string
    experience: string
    location: string
    language: string
    certificates: string[]
  }
  seniority_hint: string
}

interface V2Result {
  schema_version: string
  match_score: number
  matched_skills: string[]
  gap_skills: V2GapSkill[]
  strengths: string[]
  risks: string[]
  resume_tips: string[]
  action_suggestions: string[]
}

interface V2DiagnosisResponse {
  id: number
  match_score: number
  jd_title: string
  company: string
  jd_text: string
  jd_extract: V2JDExtract
  result: V2Result
  created_at: string
  warnings: string[]
}

interface V2ListItem {
  id: number
  jd_title: string
  company: string
  match_score: number
  created_at: string
}

/* ── adapter: flatten v2 nested result into v1-compatible shape ── */

function adaptV2Response(res: V2DiagnosisResponse): JDDiagnosisDetail {
  return {
    id: res.id,
    jd_title: res.jd_title,
    jd_text: res.jd_text,
    match_score: res.match_score,
    created_at: res.created_at,
    matched_skills: res.result.matched_skills,
    gap_skills: res.result.gap_skills,
    extracted_skills: [
      ...res.jd_extract.required_skills,
      ...res.jd_extract.preferred_skills,
    ],
    resume_tips: res.result.resume_tips,
    dimensions: {},
    graph_context: null,
    coach_insight: null,
  }
}
