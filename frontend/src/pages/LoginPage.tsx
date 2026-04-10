import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'

export default function LoginPage() {
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [tab, setTab] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const card1Ref = useRef<HTMLDivElement>(null)
  const card2Ref = useRef<HTMLDivElement>(null)
  const card3Ref = useRef<HTMLDivElement>(null)
  const loginCardRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isAuthenticated) navigate('/', { replace: true })
  }, [isAuthenticated, navigate])

  /* Parallax depth on mouse move */
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const cx = (e.clientX / window.innerWidth - 0.5) * 2
      const cy = (e.clientY / window.innerHeight - 0.5) * 2
      const refs = [card1Ref, card2Ref, card3Ref]
      const depths = [18, 12, 7]
      const baseRots = [-4, 3, 2.5]
      refs.forEach((ref, i) => {
        if (ref.current) {
          const rx = baseRots[i] + cy * 1.5
          ref.current.style.transform = `rotate(${rx}deg) translateX(${cx * depths[i]}px) translateY(${cy * depths[i]}px)`
        }
      })
      if (loginCardRef.current) {
        loginCardRef.current.style.transform = `translateX(${cx * -2}px) translateY(${cy * -2}px)`
      }
    }
    document.addEventListener('mousemove', handleMouseMove)
    return () => document.removeEventListener('mousemove', handleMouseMove)
  }, [])

  const switchTab = (t: 'login' | 'register') => {
    setTab(t)
    setError('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password.trim()) {
      setError('请输入用户名和密码')
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

  return (
    <div className="min-h-screen overflow-hidden font-sans" style={{ background: '#fafafa', color: '#171717' }}>

      {/* Ambient glow */}
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        <motion.div
          className="absolute rounded-full"
          style={{
            width: 700, height: 700, top: -250, right: -150,
            background: 'radial-gradient(circle, rgba(37,99,235,0.12) 0%, transparent 65%)',
          }}
          animate={{ x: [0, 50], y: [0, 40], scale: [1, 1.05] }}
          transition={{ duration: 20, repeat: Infinity, repeatType: 'reverse', ease: 'easeInOut' }}
        />
        <motion.div
          className="absolute rounded-full"
          style={{
            width: 600, height: 600, bottom: -200, left: -150,
            background: 'radial-gradient(circle, rgba(37,99,235,0.08) 0%, transparent 60%)',
          }}
          animate={{ x: [0, -50], y: [0, -40], scale: [1, 1.05] }}
          transition={{ duration: 24, repeat: Infinity, repeatType: 'reverse', ease: 'easeInOut' }}
        />
      </div>

      <div className="relative z-10 min-h-screen flex items-center justify-center px-5 py-10">

        {/* Depth card 1 */}
        <div
          ref={card1Ref}
          className="absolute top-[8%] left-[8%] w-[420px] h-[340px] hidden md:block rounded-[20px] border border-black/[0.08] bg-white overflow-hidden pointer-events-none z-[1]"
          style={{ opacity: 0.5, filter: 'blur(3px)', boxShadow: '0 12px 32px rgba(0,0,0,0.08)', animation: 'depth-float-1 12s ease-in-out infinite' }}
        >
          <div className="p-7">
            <DcHeader />
            <DcNav />
            <DcLine w="95%" /><DcLine w="80%" /><DcLine w="60%" />
            <DcChart />
          </div>
        </div>

        {/* Depth card 2 */}
        <div
          ref={card2Ref}
          className="absolute bottom-[10%] right-[6%] w-[380px] h-[300px] hidden md:block rounded-[20px] border border-black/[0.08] bg-white overflow-hidden pointer-events-none z-[2]"
          style={{ opacity: 0.65, filter: 'blur(2px)', boxShadow: '0 12px 32px rgba(0,0,0,0.08)', animation: 'depth-float-2 14s ease-in-out infinite' }}
        >
          <div className="p-6">
            <DcHeader />
            <DcStats />
            <div className="mt-4">
              <DcLine w="95%" /><DcLine w="70%" accent /><DcLine w="80%" /><DcLine w="60%" />
            </div>
            <DcBtnRow />
          </div>
        </div>

        {/* Depth card 3 */}
        <div
          ref={card3Ref}
          className="absolute top-[14%] right-[12%] w-[350px] h-[260px] hidden md:block rounded-[20px] border border-black/[0.08] bg-white overflow-hidden pointer-events-none z-[3]"
          style={{ opacity: 0.8, filter: 'blur(1px)', boxShadow: '0 12px 32px rgba(0,0,0,0.08)', animation: 'depth-float-3 10s ease-in-out infinite' }}
        >
          <div className="p-6">
            <DcHeader />
            <DcProfile />
            <DcLine w="95%" /><DcLine w="70%" accent /><DcLine w="80%" /><DcLine w="95%" /><DcLine w="60%" />
            <DcBtnRow />
          </div>
        </div>

        {/* Main login card */}
        <motion.div
          ref={loginCardRef}
          initial={{ opacity: 0, y: 30, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.7, ease: [0.23, 1, 0.32, 1] }}
          className="relative z-10 w-full max-w-[420px] bg-white border border-black/[0.08] rounded-3xl px-10 pb-10 pt-12"
          style={{ boxShadow: '0 24px 64px rgba(0,0,0,0.10), 0 8px 24px rgba(0,0,0,0.06), 0 0 0 1px rgba(0,0,0,0.04), 0 0 60px rgba(37,99,235,0.08)' }}
        >
          {/* Top accent line */}
          <div
            className="absolute -top-px left-[15%] right-[15%] h-px rounded"
            style={{ background: 'linear-gradient(90deg, transparent, rgba(37,99,235,0.15), transparent)' }}
          />

          {/* Logo */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.6 }}
            className="text-center mb-9"
          >
            <div
              className="inline-flex items-center justify-center w-20 h-20 mb-5 rounded-[20px] border p-3"
              style={{
                background: 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)',
                borderColor: '#93c5fd',
                boxShadow: '0 4px 16px rgba(37,99,235,0.10)',
              }}
            >
              <img src="logo.png" alt="职途智析" className="w-full h-full object-contain" />
            </div>
            <h1 className="text-[26px] font-bold tracking-tight text-[#171717]">职途智析</h1>
            <p className="text-sm text-[#525252] mt-1.5">AI 驱动的职业规划助手</p>
          </motion.div>

          {/* Tabs */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.6 }}
            className="flex bg-[#f5f5f5] rounded-xl p-1 mb-8"
          >
            {(['login', 'register'] as const).map((t) => (
              <button
                key={t}
                onClick={() => switchTab(t)}
                className={`flex-1 py-2.5 text-sm font-semibold rounded-[10px] transition-all duration-[250ms] cursor-pointer border-none font-sans ${
                  tab === t
                    ? 'bg-white text-[#171717] shadow-sm'
                    : 'bg-transparent text-[#a3a3a3] hover:text-[#525252]'
                }`}
              >
                {t === 'login' ? '登录' : '注册'}
              </button>
            ))}
          </motion.div>

          {/* Form */}
          <form onSubmit={handleSubmit}>
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, duration: 0.6 }}
              className="mb-5"
            >
              <label className="block text-[13px] font-medium text-[#525252] mb-2 tracking-[0.01em]">
                用户名
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="请输入用户名"
                autoComplete="off"
                className="w-full px-4 py-[13px] bg-white border-[1.5px] border-black/[0.08] rounded-xl text-[15px] text-[#171717] outline-none transition-all font-sans placeholder:text-[#a3a3a3] hover:border-black/[0.12] focus:border-blue-600 focus:shadow-[0_0_0_4px_rgba(37,99,235,0.08)]"
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25, duration: 0.6 }}
              className="mb-5"
            >
              <label className="block text-[13px] font-medium text-[#525252] mb-2 tracking-[0.01em]">
                密码
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="请输入密码"
                autoComplete="off"
                className="w-full px-4 py-[13px] bg-white border-[1.5px] border-black/[0.08] rounded-xl text-[15px] text-[#171717] outline-none transition-all font-sans placeholder:text-[#a3a3a3] hover:border-black/[0.12] focus:border-blue-600 focus:shadow-[0_0_0_4px_rgba(37,99,235,0.08)]"
              />
            </motion.div>

            {tab === 'login' && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3, duration: 0.6 }}
                className="flex items-center justify-between mb-7"
              >
                <label className="flex items-center gap-2.5 cursor-pointer text-[13px] text-[#525252]">
                  <input type="checkbox" className="accent-blue-600 w-[18px] h-[18px] cursor-pointer rounded" />
                  <span>记住我</span>
                </label>
                <a href="#" className="text-[13px] text-blue-600 font-medium hover:opacity-70 transition-opacity">
                  忘记密码?
                </a>
              </motion.div>
            )}

            {error && (
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-4 px-4 py-2.5 text-[13px] text-red-600 text-center bg-red-600/[0.06] rounded-lg"
              >
                {error}
              </motion.div>
            )}

            <motion.button
              type="submit"
              disabled={loading}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.35, duration: 0.6 }}
              whileHover={!loading ? { y: -2, boxShadow: '0 8px 28px rgba(37,99,235,0.4)' } : undefined}
              whileTap={!loading ? { y: 0 } : undefined}
              className="w-full py-[14px] rounded-xl text-[15px] font-semibold text-white cursor-pointer border-none font-sans disabled:opacity-70 disabled:cursor-not-allowed"
              style={{
                background: 'linear-gradient(135deg, #2563eb, #1d4ed8)',
                boxShadow: '0 4px 16px rgba(37,99,235,0.3)',
              }}
            >
              {loading
                ? (tab === 'login' ? '登录中...' : '注册中...')
                : (tab === 'login' ? '登录' : '注册')}
            </motion.button>
          </form>

          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.6 }}
            className="text-center mt-7 text-sm text-[#525252]"
          >
            {tab === 'login' ? '还没有账号？' : '已有账号？'}
            <button
              onClick={() => switchTab(tab === 'login' ? 'register' : 'login')}
              className="text-blue-600 font-semibold hover:opacity-70 transition-opacity cursor-pointer border-none bg-transparent font-sans ml-0.5"
            >
              {tab === 'login' ? '立即注册' : '立即登录'}
            </button>
          </motion.p>
        </motion.div>
      </div>
    </div>
  )
}

/* ── Decorative sub-components for depth cards ── */

function DcHeader() {
  return (
    <div className="flex items-center gap-2 mb-[18px]">
      <div className="w-2 h-2 rounded-full bg-red-200" />
      <div className="w-2 h-2 rounded-full bg-yellow-200" />
      <div className="w-2 h-2 rounded-full bg-green-200" />
      <div className="flex-1 h-2.5 rounded bg-black/[0.06] ml-2" />
    </div>
  )
}

function DcNav() {
  return (
    <div className="flex gap-1.5 mb-3.5">
      {['概览', '技能', '路径', '报告'].map((item, i) => (
        <span
          key={item}
          className={`px-3 py-[5px] rounded-[5px] text-[9px] font-medium ${
            i === 0 ? 'bg-blue-600/[0.08] text-blue-600' : 'bg-black/[0.03] text-black/25'
          }`}
        >
          {item}
        </span>
      ))}
    </div>
  )
}

function DcLine({ w, accent }: { w: string; accent?: boolean }) {
  return (
    <div
      className="h-2 rounded mb-2.5"
      style={{
        width: w,
        background: accent
          ? 'linear-gradient(90deg, rgba(37,99,235,0.08), transparent)'
          : 'rgba(0,0,0,0.04)',
      }}
    />
  )
}

function DcChart() {
  const heights = [40, 65, 50, 80, 60, 75, 45]
  return (
    <div className="flex items-end gap-1.5 h-20 mt-4">
      {heights.map((h, i) => (
        <div
          key={i}
          className="flex-1 rounded-t"
          style={{
            height: `${h}%`,
            background: i === 3 ? 'rgba(37,99,235,0.25)' : 'rgba(37,99,235,0.12)',
          }}
        />
      ))}
    </div>
  )
}

function DcStats() {
  return (
    <div className="flex gap-3 mt-3">
      {['87%', '12', 'A+'].map((val, i) => (
        <div key={i} className="flex-1 p-2.5 rounded-lg bg-black/[0.02] border border-black/[0.04]">
          <div className="text-lg font-bold mb-0.5" style={{ color: 'rgba(37,99,235,0.6)' }}>{val}</div>
          <div className="h-1.5 w-1/2 rounded bg-black/[0.06]" />
        </div>
      ))}
    </div>
  )
}

function DcProfile() {
  return (
    <div className="flex items-center gap-3 mb-3.5">
      <div className="w-9 h-9 rounded-full flex-shrink-0" style={{ background: 'rgba(37,99,235,0.08)' }} />
      <div className="flex-1">
        <div className="h-2.5 rounded mb-1.5 bg-black/[0.06]" style={{ width: '80%' }} />
        <div className="h-1.5 rounded bg-black/[0.04]" style={{ width: '60%' }} />
      </div>
    </div>
  )
}

function DcBtnRow() {
  return (
    <div className="flex gap-2 mt-3.5">
      <span className="px-4 py-1.5 rounded-[6px] text-[10px] font-semibold bg-blue-600/[0.08] text-blue-600">
        开始评估
      </span>
      <span className="px-4 py-1.5 rounded-[6px] text-[10px] font-semibold border border-black/[0.08] text-black/35">
        查看详情
      </span>
    </div>
  )
}
