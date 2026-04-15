import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '@/hooks/useAuth'

export default function LoginPage() {
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [tab, setTab] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (isAuthenticated) navigate('/', { replace: true })
  }, [isAuthenticated, navigate])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password.trim()) {
      setError('用户名和密码都填一下')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`/api/auth/${tab}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail || '没通过 —— 再试一下')
        return
      }
      if (data.success && data.data?.token) {
        localStorage.setItem('token', data.data.token)
        localStorage.setItem('user', JSON.stringify(data.data.user))
        navigate('/')
      } else {
        setError(data.message || '没通过 —— 再试一下')
      }
    } catch {
      setError('连不上后端 —— 检查一下服务')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-[var(--bg-paper)] flex items-center justify-center px-6 py-20">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
        className="w-full max-w-[420px]"
      >
        <p className="font-sans text-[13px] font-bold uppercase tracking-[0.22em] text-[var(--chestnut)] mb-5">
          Editorial · 职途智析
        </p>

        <AnimatePresence mode="wait">
          <motion.h1
            key={tab}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="font-display font-medium text-[var(--fs-display-lg)] leading-[var(--lh-display)] text-[var(--ink-1)] tracking-tight"
          >
            {tab === 'login' ? '登录' : '注册'}
          </motion.h1>
        </AnimatePresence>

        <p className="mt-3 font-sans text-[var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-2)]">
          一份只给你自己的档案。
        </p>

        <div className="mt-10 mb-8 h-px bg-[var(--line)]" />

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block font-sans text-[var(--fs-body-sm)] text-[var(--ink-3)] mb-2">用户名</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              className="w-full px-4 py-3 bg-[var(--bg-card)] border border-[var(--line)] rounded-md text-[var(--fs-body)] text-[var(--ink-1)] outline-none focus:border-[var(--chestnut)]/60 focus:ring-2 focus:ring-[var(--chestnut)]/20 transition-colors"
            />
          </div>
          <div>
            <label className="block font-sans text-[var(--fs-body-sm)] text-[var(--ink-3)] mb-2">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
              className="w-full px-4 py-3 bg-[var(--bg-card)] border border-[var(--line)] rounded-md text-[var(--fs-body)] text-[var(--ink-1)] outline-none focus:border-[var(--chestnut)]/60 focus:ring-2 focus:ring-[var(--chestnut)]/20 transition-colors"
            />
          </div>

          {error && (
            <p className="text-[var(--fs-body-sm)] text-[var(--ember)]">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-md bg-[var(--chestnut)] text-white text-[var(--fs-body)] font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {loading ? (tab === 'login' ? '登录中…' : '注册中…') : (tab === 'login' ? '登录' : '注册')}
          </button>
        </form>

        <p className="mt-8 text-[var(--fs-body-sm)] text-[var(--ink-3)]">
          {tab === 'login' ? '没有账号？' : '已有账号？'}
          <button
            type="button"
            onClick={() => {
              setTab(tab === 'login' ? 'register' : 'login')
              setError('')
            }}
            className="ml-2 text-[var(--ink-1)] underline underline-offset-4 hover:text-[var(--chestnut)] transition-colors"
          >
            {tab === 'login' ? '立即注册 →' : '立即登录 →'}
          </button>
        </p>
      </motion.div>
    </main>
  )
}
