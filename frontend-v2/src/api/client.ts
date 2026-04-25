export const API_BASE = '/api'

let _isRedirecting = false

/** Clear auth state and redirect to login page */
function handleUnauthorized(): never {
  if (_isRedirecting) {
    // Another 401 already triggered the redirect — abort this request,
    // let the in-flight navigation complete. Do NOT busy-wait (would freeze the UI).
    throw new Error('Unauthorized (redirect in progress)')
  }
  _isRedirecting = true
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  window.dispatchEvent(new Event('auth-change'))
  window.location.href = '/login'
  throw new Error('Unauthorized')
}

/** Shared fetch with auth — returns raw JSON (no wrapper). */
export async function rawFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token')
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string>),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`
  if (!init?.body || typeof init.body === 'string') {
    headers['Content-Type'] = headers['Content-Type'] ?? 'application/json'
  }

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers })

  if (res.status === 401) handleUnauthorized()

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail || `请求失败 (${res.status})`)
  }

  // 204 No Content — no body to parse
  if (res.status === 204) return undefined as unknown as T

  return res.json() as Promise<T>
}

export async function apiFetch<T = unknown>(
  path: string,
  init?: RequestInit,
): Promise<{ success: boolean; data?: T; message?: string }> {
  return rawFetch<{ success: boolean; data?: T; message?: string }>(path, init)
}

export async function apiUpload<T = unknown>(
  path: string,
  file: File,
): Promise<{ success: boolean; data?: T; message?: string }> {
  const form = new FormData()
  form.append('file', file)
  return rawFetch<{ success: boolean; data?: T; message?: string }>(path, {
    method: 'POST',
    body: form,
  })
}
