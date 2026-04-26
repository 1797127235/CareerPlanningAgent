import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

const t = {
  ink: '#1F1F1F',
  inkSecondary: '#6B6560',
  inkMuted: '#9A9590',
  button: '#6B3E2E',
  buttonHover: '#5A3426',
  line: '#D9D4CC',
} as const

const serif = { fontFamily: 'var(--font-serif), Georgia, "Noto Serif SC", serif' }
const sans = { fontFamily: 'var(--font-sans), "Noto Sans SC", system-ui, sans-serif' }
const containerClass = 'mx-auto w-full max-w-[1440px] px-6 md:px-12'

export default function Navbar() {
  const navigate = useNavigate()
  const location = useLocation()
  const [open, setOpen] = useState(false)

  const links = [
    { label: '能力画像', route: '/profile' },
    { label: '成长手札', route: '/growth-log' },
    { label: '职位地图', route: '/graph' },
    { label: '方法卷宗', route: '/coach/chat' },
  ]

  return (
    <nav
      className="fixed left-0 right-0 top-0 z-50"
      style={{ background: 'var(--bg-paper)', borderBottom: `1px solid ${t.line}` }}
    >
      <div className={`${containerClass} flex h-[64px] items-center justify-between`}>
        <button
          onClick={() => navigate('/')}
          className="text-[17px] font-semibold tracking-tight transition-opacity duration-200 hover:opacity-60"
          style={{ ...serif, color: t.ink }}
        >
          CareerPlan
        </button>

        <div className="hidden items-center gap-8 md:flex">
          {links.map((l) => {
            const active = location.pathname === l.route || location.pathname.startsWith(l.route + '/')
            return (
              <button
                key={l.route}
                onClick={() => navigate(l.route)}
                className="text-[15px] font-medium transition-colors duration-200"
                style={{ ...sans, color: active ? t.ink : t.inkSecondary }}
                onMouseEnter={(e) => { e.currentTarget.style.color = t.ink }}
                onMouseLeave={(e) => { e.currentTarget.style.color = active ? t.ink : t.inkSecondary }}
              >
                {l.label}
              </button>
            )
          })}
          <button
            onClick={() => navigate('/login')}
            className="ml-2 rounded-md px-4 py-2 text-[13px] font-medium text-white transition-colors duration-200"
            style={{ background: t.button, ...sans }}
            onMouseEnter={(e) => { e.currentTarget.style.background = t.buttonHover }}
            onMouseLeave={(e) => { e.currentTarget.style.background = t.button }}
          >
            启程分析
          </button>
        </div>

        <button
          className="flex flex-col gap-1.5 p-2 md:hidden"
          style={{ background: 'none', border: 'none', cursor: 'pointer' }}
          onClick={() => setOpen(!open)}
          aria-label="菜单"
        >
          <span className="block w-5" style={{ borderTop: `1.5px solid ${t.inkSecondary}` }} />
          <span className="block w-5" style={{ borderTop: `1.5px solid ${t.inkSecondary}` }} />
        </button>
      </div>

      {open && (
        <div
          className="flex flex-col gap-3 px-6 py-4 md:hidden"
          style={{ borderTop: `1px solid ${t.line}` }}
        >
          {links.map((l) => (
            <button
              key={l.route}
              onClick={() => { navigate(l.route); setOpen(false) }}
              className="text-left text-[15px]"
              style={{ ...sans, color: t.inkSecondary }}
            >
              {l.label}
            </button>
          ))}
          <button
            onClick={() => { navigate('/login'); setOpen(false) }}
            className="mt-1 w-fit rounded-md px-4 py-2 text-[13px] font-medium text-white"
            style={{ background: t.button, ...sans }}
          >
            开始分析
          </button>
        </div>
      )}
    </nav>
  )
}
