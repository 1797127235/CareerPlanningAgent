import { useCallback, useSyncExternalStore } from 'react'
import { useNavigate } from 'react-router-dom'
import type { User } from '@/types/user'

export type { User }

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  logout: () => void
}

/* ── Snapshot caches for useSyncExternalStore ── */
let cachedToken: string | null | undefined = undefined
let cachedUser: User | null | undefined = undefined
let lastRawToken: string | null = '__init__'
let lastRawUser: string | null = '__init__'

function readUser(): User | null {
  try {
    const raw = localStorage.getItem('user')
    if (raw === lastRawUser) return cachedUser ?? null
    lastRawUser = raw
    if (!raw) {
      cachedUser = null
      return null
    }
    cachedUser = JSON.parse(raw) as User
    return cachedUser
  } catch {
    lastRawUser = null
    cachedUser = null
    return null
  }
}

function getToken(): string | null {
  try {
    const raw = localStorage.getItem('token')
    if (raw === lastRawToken) return cachedToken ?? null
    lastRawToken = raw
    cachedToken = raw
    return raw
  } catch {
    lastRawToken = null
    cachedToken = null
    return null
  }
}

function subscribe(callback: () => void) {
  const handler = (e: StorageEvent) => {
    if (e.key === 'token' || e.key === 'user') {
      callback()
    }
  }
  window.addEventListener('storage', handler)
  const customHandler = () => callback()
  window.addEventListener('auth-change', customHandler)
  return () => {
    window.removeEventListener('storage', handler)
    window.removeEventListener('auth-change', customHandler)
  }
}

function dispatchAuthChange() {
  window.dispatchEvent(new Event('auth-change'))
}

export function useAuth(): AuthState {
  const token = useSyncExternalStore(subscribe, getToken, () => null)
  const user = useSyncExternalStore(subscribe, readUser, () => null)
  const navigate = useNavigate()

  const isAuthenticated = Boolean(token && user)

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    dispatchAuthChange()
    navigate('/login', { replace: true })
  }, [navigate])

  return { token, user, isAuthenticated, logout }
}

/** Call this after login to notify all useAuth consumers */
export function notifyAuthChange() {
  dispatchAuthChange()
}
