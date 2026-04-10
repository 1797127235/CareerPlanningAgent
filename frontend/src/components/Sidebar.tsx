import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Map,
  FileText,
  Menu,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  Home,
  FolderKanban,
  CircleUser,
} from 'lucide-react'
import type { User } from '@/types/user'
import { useAuth } from '@/hooks/useAuth'

interface SidebarProps {
  user: User | null
}

const navItems = [
  { key: 'home',         label: '首页',    icon: Home,          route: '/' },
  { key: 'profile',      label: '我的画像', icon: CircleUser,    route: '/profile' },
  { key: 'graph',        label: '岗位图谱', icon: Map,           route: '/graph' },
  { key: 'growth-log',   label: '成长档案', icon: FolderKanban,  route: '/growth-log' },
  { key: 'report',       label: '发展报告', icon: FileText,      route: '/report' },
] as const

function routeToKey(pathname: string): string {
  const match = navItems.find((n) => n.route === pathname || pathname.startsWith(n.route + '/'))
  return match?.key ?? 'home'
}

export function Sidebar({ user }: SidebarProps) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const { logout } = useAuth()

  const activeNav = routeToKey(location.pathname)
  const avatarLetter = user?.username?.charAt(0).toUpperCase() ?? 'U'
  const displayName = user?.username ?? 'User'

  function handleNavClick(key: string) {
    setMobileOpen(false)
    const item = navItems.find((n) => n.key === key)
    if (item?.route) navigate(item.route)
  }

  return (
    <>
      {/* Mobile toggle button */}
      <header className="md:hidden h-14 flex items-center justify-between px-4 z-20 fixed top-0 left-0 right-0 glass-nav">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 shrink-0" viewBox="0 0 28 28" fill="none">
            <defs>
              <linearGradient id="logo-bg-m" x1="0" y1="0" x2="28" y2="28">
                <stop offset="0%" stopColor="#2563EB"/>
                <stop offset="100%" stopColor="#60a5fa"/>
              </linearGradient>
            </defs>
            <rect width="28" height="28" rx="7" fill="url(#logo-bg-m)"/>
            <path d="M8 19L14 13L20 9" stroke="white" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
            <circle cx="8" cy="19" r="2" fill="white" opacity="0.55"/>
            <circle cx="14" cy="13" r="2" fill="white" opacity="0.8"/>
            <circle cx="20" cy="9" r="2.2" fill="white"/>
          </svg>
          <span className="font-semibold text-slate-800 text-[15px] tracking-[0.04em]">
            职途智析
          </span>
        </div>
        <button
          onClick={() => setMobileOpen(true)}
          className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
        >
          <Menu className="w-5 h-5" />
        </button>
      </header>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-slate-900/20 backdrop-blur-sm z-40 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          ${collapsed ? 'w-[68px]' : 'w-[220px]'} h-full glass-nav flex flex-col flex-shrink-0 relative
          transition-all duration-300 ease-[cubic-bezier(0.23,1,0.32,1)]
          md:translate-x-0
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}
          fixed md:static z-50
        `}
      >
        {/* Logo */}
        <div className={`h-14 flex items-center ${collapsed ? 'justify-center' : 'justify-between'} px-4 shrink-0 border-b border-black/[0.06]`}>
          {!collapsed && (
            <div
              onClick={() => { navigate('/'); setMobileOpen(false) }}
              className="flex items-center gap-2 cursor-pointer group"
            >
              <svg className="w-[22px] h-[22px] shrink-0 transition-transform duration-200 group-hover:scale-105" viewBox="0 0 24 24" fill="none">
                <defs>
                  <linearGradient id="logo-g" x1="4" y1="20" x2="20" y2="4">
                    <stop offset="0%" stopColor="#2563EB"/>
                    <stop offset="100%" stopColor="#60a5fa"/>
                  </linearGradient>
                </defs>
                <path d="M4 18L10.5 11.5L15 14L20 6" stroke="url(#logo-g)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
                <circle cx="20" cy="6" r="2.5" fill="#2563EB"/>
              </svg>
              <span className="font-semibold text-slate-800 text-[15px] tracking-[0.02em] group-hover:text-[var(--blue)] transition-colors duration-200">
                职途智析
              </span>
            </div>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="hidden md:flex p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-200/50 rounded-lg transition-colors cursor-pointer"
            title={collapsed ? '展开侧栏' : '收起侧栏'}
          >
            {collapsed ? <PanelLeftOpen className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 overflow-y-auto no-scrollbar">
          {!collapsed && (
            <div className="px-2 pb-2 pt-3">
              <span className="text-[11.5px] font-semibold text-slate-400/80 uppercase tracking-widest">
                功能
              </span>
            </div>
          )}
          {collapsed && <div className="pt-3" />}

          <div className="space-y-0.5">
            {navItems.map((item) => {
              const Icon = item.icon
              const isActive = activeNav === item.key
              return (
                <div
                  key={item.key}
                  onClick={() => handleNavClick(item.key)}
                  title={collapsed ? item.label : undefined}
                  className={`
                    flex items-center ${collapsed ? 'justify-center' : 'gap-3'} h-10 ${collapsed ? 'px-0 mx-auto w-10' : 'px-2.5'} rounded-lg text-[14px] font-medium cursor-pointer select-none
                    transition-all duration-150 relative
                    ${
                      isActive
                        ? 'bg-white/60 text-slate-900 shadow-[0_2px_8px_rgba(0,0,0,0.06)] backdrop-blur-[12px] border border-white/50'
                        : 'text-slate-500 hover:bg-white/30 hover:text-slate-700'
                    }
                  `}
                >
                  {isActive && !collapsed && (
                    <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[2.5px] h-4 bg-[var(--blue)] rounded-r-full" />
                  )}
                  <Icon
                    className={`w-[18px] h-[18px] shrink-0 ${isActive ? 'text-[var(--blue)]' : 'text-slate-400'}`}
                  />
                  {!collapsed && <span>{item.label}</span>}
                </div>
              )
            })}
          </div>
        </nav>

        {/* User info */}
        <div className={`${collapsed ? 'mx-2 mb-3 px-0 py-2 justify-center' : 'mx-3 mb-3 px-3 py-3'} rounded-lg bg-white/40 border border-white/40 backdrop-blur-[10px] flex items-center gap-3 shrink-0 hover:bg-white/55 transition-all duration-150 cursor-default`}>
          <div className="w-8 h-8 rounded-full bg-[var(--blue)]/10 border border-[var(--blue)]/20 flex items-center justify-center text-[var(--blue)] font-semibold text-[12px] shrink-0">
            {avatarLetter}
          </div>
          {!collapsed && (
            <>
              <span className="text-[14px] font-medium text-slate-700 flex-1 truncate">{displayName}</span>
              <button
                onClick={logout}
                className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-md transition-colors shrink-0"
                title="退出登录"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </aside>
    </>
  )
}
