import { useState, useEffect, useCallback } from 'react'
import { API_BASE } from '@/api/client'

export interface ChatSession {
  id: number
  title: string
  updated_at: string
}

export interface SessionGroup {
  group: string
  items: ChatSession[]
}

function groupByDate(sessions: ChatSession[]): SessionGroup[] {
  const todayStart = new Date()
  todayStart.setHours(0, 0, 0, 0)
  const yesterdayStart = new Date(todayStart)
  yesterdayStart.setDate(yesterdayStart.getDate() - 1)

  const buckets: Partial<Record<string, ChatSession[]>> = {}
  for (const s of sessions) {
    const iso = s.updated_at
    const d = new Date(/Z|[+-]\d{2}:?\d{2}$/.test(iso) ? iso : iso + 'Z')
    const key = d >= todayStart ? '今天' : d >= yesterdayStart ? '昨天' : '更早'
    if (!buckets[key]) buckets[key] = []
    buckets[key]!.push(s)
  }

  return (['今天', '昨天', '更早'] as const)
    .filter((k) => (buckets[k]?.length ?? 0) > 0)
    .map((k) => ({ group: k, items: buckets[k]! }))
}

export function useSessions() {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [loading, setLoading] = useState(false)

  const refetch = useCallback(async () => {
    const token = localStorage.getItem('token')
    if (!token) return
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/chat/sessions`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) return
      const data: unknown = await res.json()
      setSessions(Array.isArray(data) ? (data as ChatSession[]) : [])
    } catch {
      /* silently fail — backend may not be running */
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { refetch() }, [refetch])

  const deleteSession = useCallback(async (id: number) => {
    const token = localStorage.getItem('token')
    if (!token) return
    try {
      const res = await fetch(`${API_BASE}/chat/sessions/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error((err as { detail?: string }).detail || `删除失败 (${res.status})`)
      }
      setSessions((prev) => prev.filter((s) => s.id !== id))
    } catch (e) {
      /* rethrow so caller can show error if needed */
      throw e
    }
  }, [])

  return { sessions, grouped: groupByDate(sessions), loading, refetch, deleteSession }
}
