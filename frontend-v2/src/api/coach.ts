import { rawFetch } from '@/api/client'
import type {
  CoachResultDetail,
  CoachResultListItem,
  ChatRequestBody,
} from '@/types/coach'

export async function getCoachResult(id: number): Promise<CoachResultDetail> {
  return rawFetch<CoachResultDetail>(`/coach/results/${id}`)
}

export async function listCoachResults(): Promise<CoachResultListItem[]> {
  return rawFetch<CoachResultListItem[]>('/coach/results')
}

export async function deleteCoachResult(id: number): Promise<void> {
  return rawFetch<void>(`/coach/results/${id}`, { method: 'DELETE' })
}

/* ── SSE chat stream ───────────────────────────────────────────────────────── */

let _isRedirecting = false

function handleUnauthorized(): never {
  if (_isRedirecting) {
    throw new Error('Unauthorized (redirect in progress)')
  }
  _isRedirecting = true
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  window.dispatchEvent(new Event('auth-change'))
  window.location.href = '/login'
  throw new Error('Unauthorized')
}

export async function postChat(
  body: ChatRequestBody,
  onToken: (token: string) => void,
): Promise<void> {
  const token = localStorage.getItem('token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch('/api/chat', {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  })

  if (res.status === 401) handleUnauthorized()
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail || `请求失败 (${res.status})`)
  }

  const reader = res.body?.getReader()
  if (!reader) throw new Error('无法读取流')

  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed.startsWith('data:')) continue
      const payload = trimmed.slice(5).trim()
      if (payload === '[DONE]') continue
      try {
        const json = JSON.parse(payload) as Record<string, unknown>
        if (json.card || json.agent || json.session_id) continue
        const content = json.content
        if (typeof content === 'string') {
          onToken(content)
        }
      } catch {
        // ignore non-JSON lines
      }
    }
  }
}
