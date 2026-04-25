import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Menu, X } from 'lucide-react'

const navItems = [
  { label: '档案画像', route: '/profile' },
  { label: '成长档案', route: '/growth-log' },
  { label: '岗位图谱', route: '/graph' },
] as const

export function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <div style={{ position: 'relative', zIndex: 1 }}>
      {/* Top nav */}
      <nav style={{ position: 'fixed', top: 0, left: 0, right: 0, zIndex: 50, background: 'rgba(240,235,227,0.92)', backdropFilter: 'blur(10px)', WebkitBackdropFilter: 'blur(10px)', borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 64, padding: '0 clamp(24px, 5vw, 80px)' }}>
          <div
            style={{ cursor: 'pointer', fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}
            onClick={() => navigate('/')}
          >
            CareerPlan
          </div>

          {/* Desktop links */}
          <div style={{ display: 'flex', gap: 32, alignItems: 'center' }}>
            {navItems.map((item) => (
              <a
                key={item.route}
                href={item.route}
                onClick={(e) => {
                  e.preventDefault()
                  navigate(item.route)
                }}
                style={{
                  fontSize: 14,
                  fontWeight: location.pathname === item.route || location.pathname.startsWith(item.route + '/') ? 600 : 500,
                  color: location.pathname === item.route || location.pathname.startsWith(item.route + '/') ? 'var(--text-primary)' : 'var(--text-secondary)',
                  textDecoration: 'none',
                  transition: 'color 0.2s ease',
                }}
              >
                {item.label}
              </a>
            ))}
            <button
              onClick={() => navigate('/profile')}
              className="btn btn-primary"
              style={{ padding: '8px 20px', fontSize: 13 }}
            >
              开始分析
            </button>
          </div>

          {/* Mobile toggle */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            style={{
              display: 'none',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: 4,
            }}
            className="mobile-menu-btn"
          >
            {mobileOpen ? (
              <X style={{ width: 20, height: 20, color: 'var(--text-secondary)' }} />
            ) : (
              <Menu style={{ width: 20, height: 20, color: 'var(--text-secondary)' }} />
            )}
          </button>
        </div>

        {/* Mobile menu */}
        {mobileOpen && (
          <div
            style={{
              display: 'none',
              borderTop: '1px solid var(--border-light)',
              padding: '16px 24px',
              flexDirection: 'column',
              gap: 12,
            }}
            className="mobile-menu"
          >
            {navItems.map((item) => (
              <a
                key={item.route}
                href={item.route}
                onClick={(e) => {
                  e.preventDefault()
                  navigate(item.route)
                  setMobileOpen(false)
                }}
                style={{
                  fontSize: 14,
                  fontWeight: 500,
                  color: 'var(--text-secondary)',
                  textDecoration: 'none',
                }}
              >
                {item.label}
              </a>
            ))}
            <button
              onClick={() => {
                navigate('/profile')
                setMobileOpen(false)
              }}
              className="btn btn-primary"
              style={{ width: 'fit-content', marginTop: 4 }}
            >
              开始分析
            </button>
          </div>
        )}
      </nav>

      {/* Page content */}
      <main style={{ paddingTop: 64 }}>
        <Outlet />
      </main>
    </div>
  )
}
