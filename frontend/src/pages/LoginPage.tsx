import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { User, Lock, Eye, EyeOff, TrendingUp } from 'lucide-react'

export default function LoginPage() {
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [tab, setTab] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const card1Ref = useRef<HTMLDivElement>(null)
  const card2Ref = useRef<HTMLDivElement>(null)
  const card3Ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isAuthenticated) navigate('/', { replace: true })
  }, [isAuthenticated, navigate])

  /* Parallax depth on mouse move */
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const cx = (e.clientX / window.innerWidth - 0.5) * 2
      const cy = (e.clientY / window.innerHeight - 0.5) * 2
      const refs = [card1Ref, card2Ref, card3Ref]
      const depths = [10, 7, 4]
      const baseRots = [-4, 3, 2.5]
      refs.forEach((ref, i) => {
        if (ref.current) {
          const rx = baseRots[i] + cy * 1.5
          ref.current.style.transform = `rotate(${rx}deg) translateX(${cx * depths[i]}px) translateY(${cy * depths[i]}px)`
        }
      })
    }
    document.addEventListener('mousemove', handleMouseMove)
    return () => document.removeEventListener('mousemove', handleMouseMove)
  }, [])

  const switchTab = (t: 'login' | 'register') => {
    setTab(t)
    setError('')
    setConfirmPassword('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password.trim()) {
      setError('请输入用户名和密码')
      return
    }
    if (tab === 'register' && password !== confirmPassword) {
      setError('两次输入的密码不一致')
      return
    }
    setLoading(true)
    setError('')
    try {
      const endpoint = tab === 'login' ? '/api/auth/login' : '/api/auth/register'
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail || '操作失败')
        return
      }
      if (data.success && data.data?.token) {
        localStorage.setItem('token', data.data.token)
        localStorage.setItem('user', JSON.stringify(data.data.user))
        navigate('/')
      } else {
        setError(data.message || '操作失败')
      }
    } catch {
      setError('网络错误，请检查后端是否启动')
    } finally {
      setLoading(false)
    }
  }

  const decorGlass: React.CSSProperties = {
    background: 'rgba(255,255,255,0.65)',
    backdropFilter: 'blur(12px) saturate(140%)',
    WebkitBackdropFilter: 'blur(12px) saturate(140%)',
    border: '1px solid rgba(255,255,255,0.30)',
    borderRadius: '16px',
    boxShadow: '0 4px 16px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.50)',
  }

  return (
    <div className="min-h-screen overflow-hidden font-sans relative text-[var(--text-1)]">
      <div className="bg-canvas" />

      {/* Ambient glow */}
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        <motion.div
          className="absolute rounded-full"
          style={{
            width: 600, height: 600, top: -200, right: -120,
            background: 'radial-gradient(circle, oklch(0.90 0.05 240 / 0.35) 0%, transparent 65%)',
          }}
          animate={{ x: [0, 40], y: [0, 30], scale: [1, 1.06] }}
          transition={{ duration: 17, repeat: Infinity, repeatType: 'reverse', ease: 'easeInOut' }}
        />
        <motion.div
          className="absolute rounded-full"
          style={{
            width: 520, height: 520, bottom: -160, left: -120,
            background: 'radial-gradient(circle, oklch(0.90 0.05 240 / 0.25) 0%, transparent 60%)',
          }}
          animate={{ x: [0, -40], y: [0, -30], scale: [1, 1.05] }}
          transition={{ duration: 23, repeat: Infinity, repeatType: 'reverse', ease: 'easeInOut' }}
        />
      </div>

      <div className="relative z-10 min-h-screen flex items-center justify-center px-5 py-10">

        {/* Depth card 1 — Skill tags */}
        <div
          ref={card1Ref}
          className="absolute top-[8%] left-[8%] w-[400px] h-[300px] hidden md:block overflow-hidden pointer-events-none z-[1]"
          style={{ ...decorGlass, opacity: 0.5, filter: 'blur(3px)', animation: 'depth-float-1 12s ease-in-out infinite' }}
        >
          <div className="p-6">
            <DcHeader />
            <div className="flex flex-wrap gap-1.5 mt-3">
              {['Java', '产品思维', '数据分析', '英语'].map((tag) => (
                <span key={tag} className="px-2.5 py-1 rounded-full text-[10px] font-medium bg-white/50 border border-black/[0.06] text-black/40">
                  {tag}
                </span>
              ))}
            </div>
            <div className="mt-5 space-y-2">
              <div className="h-2 rounded bg-black/[0.04]" style={{ width: '90%' }} />
              <div className="h-2 rounded bg-black/[0.04]" style={{ width: '70%' }} />
              <div className="h-2 rounded bg-black/[0.04]" style={{ width: '55%' }} />
            </div>
          </div>
        </div>

        {/* Depth card 2 — Path timeline */}
        <div
          ref={card2Ref}
          className="absolute bottom-[10%] right-[6%] w-[360px] h-[260px] hidden md:block overflow-hidden pointer-events-none z-[2]"
          style={{ ...decorGlass, opacity: 0.6, filter: 'blur(2px)', animation: 'depth-float-2 14s ease-in-out infinite' }}
        >
          <div className="p-6">
            <DcHeader />
            <div className="flex items-center gap-1.5 mt-6">
              {['在校', '实习', '目标岗位'].map((n, i) => (
                <div key={n} className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-black/10" />
                  <span className="text-[10px] text-black/30 font-medium">{n}</span>
                  {i < 2 && <span className="w-8 h-px bg-black/[0.06]" />}
                </div>
              ))}
            </div>
            <div className="mt-5 space-y-2">
              <div className="h-2 rounded bg-black/[0.04]" style={{ width: '95%' }} />
              <div className="h-2 rounded bg-black/[0.04]" style={{ width: '80%' }} />
              <div className="h-2 rounded bg-black/[0.04]" style={{ width: '65%' }} />
            </div>
          </div>
        </div>

        {/* Depth card 3 — Note fragments */}
        <div
          ref={card3Ref}
          className="absolute top-[14%] right-[12%] w-[320px] h-[220px] hidden md:block overflow-hidden pointer-events-none z-[3]"
          style={{ ...decorGlass, opacity: 0.75, filter: 'blur(1px)', animation: 'depth-float-3 10s ease-in-out infinite' }}
        >
          <div className="p-6">
            <DcHeader />
            <div className="mt-4 space-y-2">
              {['整理了 3 份 JD…', '下周二面试…', '技能缺口：分布式'].map((note, i) => (
                <div key={note} className="flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-black/10" />
                  <div className="h-2 rounded bg-black/[0.04]" style={{ width: `${65 + i * 10}%` }} />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Main login card */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
          className="relative z-10 w-full max-w-[420px] glass-static px-10 pb-10 pt-12"
        >
          {/* Logo */}
          <div className="text-center mb-9">
            <div className="inline-flex items-center justify-center mb-5">
              <PathLogo />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-[var(--text-1)]">职途智析</h1>
            <p className="text-sm text-[var(--text-2)] mt-1.5">整理你的职业档案</p>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-black/[0.08] mb-8">
            {(['login', 'register'] as const).map((t) => (
              <button
                key={t}
                onClick={() => switchTab(t)}
                className={`flex-1 pb-2.5 text-sm font-semibold transition-colors cursor-pointer border-none font-sans relative ${
                  tab === t ? 'text-[var(--text-1)]' : 'text-[var(--text-3)] hover:text-[var(--text-2)]'
                }`}
              >
                {t === 'login' ? '登录' : '注册'}
                {tab === t && (
                  <motion.div
                    layoutId="tab-underline"
                    className="absolute bottom-0 left-0 right-0 h-[2px] bg-[var(--blue)]"
                    transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                  />
                )}
              </button>
            ))}
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit}>
            <div className="mb-5">
              <label className="block text-[13px] font-medium text-[var(--text-2)] mb-2 tracking-[0.01em]">
                用户名
              </label>
              <div className="relative">
                <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-3)] pointer-events-none" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="请输入用户名"
                  autoComplete="off"
                  className="w-full pl-10 pr-4 py-[13px] bg-white/50 border border-black/[0.08] rounded-xl text-[15px] text-[var(--text-1)] outline-none transition-all font-sans placeholder:text-[var(--text-3)] hover:border-black/[0.12] focus:border-[var(--blue)] focus:bg-white/70"
                  style={{ boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.02)' }}
                />
              </div>
            </div>

            <div className="mb-5">
              <label className="block text-[13px] font-medium text-[var(--text-2)] mb-2 tracking-[0.01em]">
                密码
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-3)] pointer-events-none" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="请输入密码"
                  autoComplete="off"
                  className="w-full pl-10 pr-10 py-[13px] bg-white/50 border border-black/[0.08] rounded-xl text-[15px] text-[var(--text-1)] outline-none transition-all font-sans placeholder:text-[var(--text-3)] hover:border-black/[0.12] focus:border-[var(--blue)] focus:bg-white/70"
                  style={{ boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.02)' }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 cursor-pointer bg-transparent border-none p-0"
                >
                  {showPassword ? (
                    <EyeOff className="w-4 h-4 text-[var(--text-3)]" />
                  ) : (
                    <Eye className="w-4 h-4 text-[var(--text-3)]" />
                  )}
                </button>
              </div>
            </div>

            {tab === 'register' && (
              <div className="mb-5">
                <label className="block text-[13px] font-medium text-[var(--text-2)] mb-2 tracking-[0.01em]">
                  确认密码
                </label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-3)] pointer-events-none" />
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="请再次输入密码"
                    autoComplete="off"
                    className="w-full pl-10 pr-10 py-[13px] bg-white/50 border border-black/[0.08] rounded-xl text-[15px] text-[var(--text-1)] outline-none transition-all font-sans placeholder:text-[var(--text-3)] hover:border-black/[0.12] focus:border-[var(--blue)] focus:bg-white/70"
                    style={{ boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.02)' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 cursor-pointer bg-transparent border-none p-0"
                  >
                    {showConfirmPassword ? (
                      <EyeOff className="w-4 h-4 text-[var(--text-3)]" />
                    ) : (
                      <Eye className="w-4 h-4 text-[var(--text-3)]" />
                    )}
                  </button>
                </div>
              </div>
            )}

            {tab === 'login' && (
              <div className="flex items-center justify-between mb-6">
                <label className="flex items-center gap-2.5 cursor-pointer text-[13px] text-[var(--text-2)]">
                  <input type="checkbox" className="w-4 h-4 rounded cursor-pointer" style={{ accentColor: 'var(--blue)' }} />
                  <span>记住我</span>
                </label>
                <a href="#" className="text-[13px] text-[var(--blue)] font-medium hover:opacity-70 transition-opacity">
                  忘记密码?
                </a>
              </div>
            )}

            {error && (
              <p className="mb-5 text-xs text-red-500 text-center">{error}</p>
            )}

            <motion.button
              type="submit"
              disabled={loading}
              whileHover={!loading ? { y: -1 } : undefined}
              whileTap={!loading ? { y: 0 } : undefined}
              className="w-full py-[14px] rounded-xl text-[15px] font-semibold text-white cursor-pointer border-none font-sans disabled:opacity-70 disabled:cursor-not-allowed transition-colors"
              style={{ background: 'var(--blue)' }}
            >
              {loading
                ? (tab === 'login' ? '登录中...' : '注册中...')
                : (tab === 'login' ? '登录' : '注册')}
            </motion.button>
          </form>

          <p className="text-center mt-7 text-sm text-[var(--text-2)]">
            {tab === 'login' ? '还没有账号？' : '已有账号？'}
            <button
              onClick={() => switchTab(tab === 'login' ? 'register' : 'login')}
              className="text-[var(--blue)] font-semibold hover:opacity-70 transition-opacity cursor-pointer border-none bg-transparent font-sans ml-0.5"
            >
              {tab === 'login' ? '立即注册' : '立即登录'}
            </button>
          </p>
        </motion.div>
      </div>
    </div>
  )
}

/* ── Path logo: folded-paper career path ── */

function PathLogo() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8, y: 8 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className="inline-flex items-center justify-center w-16 h-16 rounded-2xl"
      style={{
        background: 'rgba(37,99,235,0.08)',
        border: '1.5px solid rgba(37,99,235,0.15)',
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
      >
        <TrendingUp className="w-7 h-7" style={{ color: 'var(--blue)' }} strokeWidth={2.5} />
      </motion.div>
    </motion.div>
  )
}

/* ── Decorative sub-components for depth cards ── */

function DcHeader() {
  return (
    <div className="flex items-center gap-2 mb-4">
      <div className="w-2 h-2 rounded-full bg-black/[0.08]" />
      <div className="w-2 h-2 rounded-full bg-black/[0.08]" />
      <div className="w-2 h-2 rounded-full bg-black/[0.08]" />
      <div className="flex-1 h-2 rounded bg-black/[0.04] ml-2" />
    </div>
  )
}
