import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import type { User } from '@/types/user'

export type { User }

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  logout: () => void
}

function readUser(): User | null {
  try {
    const raw = localStorage.getItem('user')
    if (!raw) return null
    return JSON.parse(raw) as User
  } catch {
    return null
  }
}

export function useAuth(): AuthState {
  const [token] = useState<string | null>(() => localStorage.getItem('token'))
  const [user] = useState<User | null>(() => readUser())
  const navigate = useNavigate()

  const isAuthenticated = Boolean(token && user)

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    navigate('/login', { replace: true })
  }, [navigate])

  return { token, user, isAuthenticated, logout }
}
