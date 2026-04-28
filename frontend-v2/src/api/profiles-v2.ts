/* ── v2 Profile API (backend2) ──
 *
 * 简历解析与保存链路 — parse-preview -> 确认/编辑 -> save
 * 与 v1 区分：parser 只提取事实，不做职业判断。
 */

const V2_BASE = '/api/v2'

async function v2RawFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token')
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string>),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`
  if (!init?.body || typeof init.body === 'string') {
    headers['Content-Type'] = headers['Content-Type'] ?? 'application/json'
  }

  const res = await fetch(`${V2_BASE}${path}`, { ...init, headers })

  if (res.status === 401) {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    window.dispatchEvent(new Event('auth-change'))
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail || `请求失败 (${res.status})`)
  }

  if (res.status === 204) return undefined as unknown as T
  return res.json() as Promise<T>
}

// ── Types ──────────────────────────────────────────────────────────────

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

// ── API ────────────────────────────────────────────────────────────────

/** 上传简历文件，返回解析预览（不保存） */
export async function parsePreview(file: File): Promise<V2ParsePreviewResponse> {
  const form = new FormData()
  form.append('file', file)
  return v2RawFetch<V2ParsePreviewResponse>('/profiles/parse-preview', {
    method: 'POST',
    body: form,
  })
}

/** 保存用户确认后的画像 */
export async function saveProfile(request: {
  raw_profile: V2ProfileData
  confirmed_profile: V2ProfileData
  document: V2ResumeDocument
  parse_meta: V2ParseMeta
}): Promise<V2SaveProfileResponse> {
  return v2RawFetch<V2SaveProfileResponse>('/profiles', {
    method: 'POST',
    body: JSON.stringify(request),
  })
}

/** 读取当前用户最新画像（v2 格式） */
export async function fetchMyProfileV2(): Promise<V2ProfileData> {
  return v2RawFetch<V2ProfileData>('/profiles/me')
}
