import { useState, useEffect, useCallback, useRef } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Bot, PanelRightOpen } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { useJustUploaded } from '@/hooks/useResumeUpload'
import { Sidebar } from '@/components/Sidebar'
import { ChatPanel } from '@/components/ChatPanel'

/* ═══════════════════════════════════════════════
   Layout — Sidebar (left) + Page (center) + Coach Panel (right)
   ═══════════════════════════════════════════════ */
export function Layout() {
  const { user } = useAuth()
  const [coachOpen, setCoachOpen] = useState(true)
  const [panelWidth, setPanelWidth] = useState(380)
  const resizing = useRef(false)
  const location = useLocation()
  const navigate = useNavigate()

  /* ── Resize handle drag ── */
  const onResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    resizing.current = true
    const startX = e.clientX
    const startW = panelWidth

    const onMove = (ev: MouseEvent) => {
      if (!resizing.current) return
      const delta = startX - ev.clientX
      const newW = Math.min(600, Math.max(280, startW + delta))
      setPanelWidth(newW)
    }
    const onUp = () => {
      resizing.current = false
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }, [panelWidth])

  // After resume upload, navigate to profile page.
  // Do NOT clear justUploaded here — ProfilePage needs to see it to fire the coach greeting.
  // Use a ref to prevent repeated navigation without consuming the shared flag.
  const { justUploaded } = useJustUploaded()
  const hasNavigatedForUpload = useRef(false)

  useEffect(() => {
    if (justUploaded && !hasNavigatedForUpload.current) {
      hasNavigatedForUpload.current = true
      navigate('/profile')
    }
    if (!justUploaded) {
      hasNavigatedForUpload.current = false
    }
  }, [justUploaded, navigate])

  // Global ext_session guard
  useEffect(() => {
    const params = new URLSearchParams(location.search)
    const extSession = params.get('ext_session')
    if (extSession && location.pathname !== '/applications') {
      navigate(`/applications?ext_session=${extSession}`, { replace: true })
    }
  }, [location.search, location.pathname, navigate])

  return (
    <div className="h-screen overflow-hidden flex text-[var(--text-1)] font-sans relative z-[1]">
      {/* Left: navigation sidebar */}
      <Sidebar user={user} />

      {/* Center: page content via Outlet */}
      <main className="flex-1 overflow-y-auto pt-14 md:pt-0 relative min-w-0">
        <Outlet />
      </main>

      {/* Right: Growth Coach panel — persistent */}
      <div
        className="hidden md:flex shrink-0 h-full relative"
        style={{ width: coachOpen ? panelWidth : 48 }}
      >
        {/* Resize handle */}
        {coachOpen && (
          // eslint-disable-next-line jsx-a11y/no-static-element-interactions
          <div
            onMouseDown={onResizeStart}
            className="absolute left-0 top-0 bottom-0 w-1 cursor-col-resize z-10 hover:bg-[var(--blue)]/20 active:bg-[var(--blue)]/30 transition-colors"
          />
        )}

        {coachOpen ? (
          <div className="flex flex-col h-full w-full border-l border-white/30">
            <ChatPanel
              open={true}
              onClose={() => setCoachOpen(false)}
              mode="panel"
            />
          </div>
        ) : (
          /* ── Collapsed coach strip ── */
          <div className="flex flex-col items-center py-4 gap-3 h-full w-full bg-white/20 backdrop-blur-sm border-l border-white/30">
            <button
              onClick={() => setCoachOpen(true)}
              className="w-10 h-10 rounded-xl bg-[var(--blue)] text-white flex items-center justify-center shadow-lg shadow-blue-500/20 hover:scale-105 active:scale-95 transition-transform cursor-pointer"
              title="展开成长教练"
            >
              <Bot className="w-5 h-5" />
            </button>
            <button
              onClick={() => setCoachOpen(true)}
              className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg transition-colors cursor-pointer"
              title="展开"
            >
              <PanelRightOpen className="w-4 h-4" />
            </button>
            <span
              className="text-[11px] font-medium text-slate-400 tracking-widest cursor-pointer hover:text-slate-600 transition-colors"
              style={{ writingMode: 'vertical-rl' }}
              onClick={() => setCoachOpen(true)}
            >
              成长教练
            </span>
          </div>
        )}
      </div>

      {/* Mobile: floating button (shows on small screens only) */}
      <div className="md:hidden">
        <MobileCoachToggle />
      </div>
    </div>
  )
}

/* ── Mobile: keep floating button behavior ── */
function MobileCoachToggle() {
  const [open, setOpen] = useState(false)

  return (
    <>
      <ChatPanel open={open} onClose={() => setOpen(false)} mode="float" />
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="
            chat-fab fixed bottom-6 right-6 z-50
            w-12 h-12 rounded-2xl
            bg-[var(--blue)] text-white
            flex items-center justify-center
            shadow-lg shadow-blue-500/25
            hover:scale-105 active:scale-95
            transition-transform cursor-pointer
          "
          title="打开成长教练"
        >
          <Bot className="w-5 h-5" />
        </button>
      )}
    </>
  )
}
