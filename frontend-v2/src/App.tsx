import { useEffect, useLayoutEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { ToastProvider } from '@/components/ui'
import { ChatPanel } from '@/components/ChatPanel'
import { MessageSquare } from 'lucide-react'
import HomePage from './pages/HomePage'
import DemoPage from './pages/DemoPage'
import ReportPage from './pages/ReportPage'
import ProfilePage from './pages/ProfilePage'
import LoginPage from './pages/LoginPage'
import GraphPage from './pages/GraphPage'
import GrowthLogPage from './pages/GrowthLogPage'
import MatchDetailPage from './pages/MatchDetailPage'
import RoleDetailPage from './pages/RoleDetailPage'
import ExplorePage from './pages/ExplorePage'
import InterviewPage from './pages/InterviewPage'
import JDDiagnosisPage from './pages/JDDiagnosisPage'
import ProjectGraphPage from './pages/ProjectGraphPage'
import PursuitDetailPage from './pages/PursuitDetailPage'
import ReportPrintPage from './pages/ReportPrintPage'
import NotFoundPage from './pages/NotFoundPage'

function ScrollReset() {
  const { pathname } = useLocation()

  useLayoutEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' })
  }, [pathname])

  return null
}

function App() {
  const [coachOpen, setCoachOpen] = useState(false)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const theme = params.get('theme')
    if (theme === 'night') document.documentElement.setAttribute('data-theme', 'night')
    else document.documentElement.removeAttribute('data-theme')
  }, [])

  return (
    <>
      {/* Global coach button — portal to body, guaranteed viewport-fixed */}
      {createPortal(
        !coachOpen && (
          <button
            onClick={() => setCoachOpen(true)}
            className="z-[9999] w-12 h-12 rounded-full bg-[#6B3E2E] text-white shadow-lg hover:bg-[#5a3324] transition-all active:scale-95 flex items-center justify-center"
            style={{ position: 'fixed', bottom: '24px', right: '24px' }}
            title="智析教练"
          >
            <MessageSquare className="w-5 h-5" />
          </button>
        ),
        document.body
      )}
      <ToastProvider>
        <BrowserRouter>
          <ScrollReset />
          {coachOpen && <ChatPanel open={coachOpen} onClose={() => setCoachOpen(false)} mode="float" />}
          <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/__demo" element={<DemoPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/report" element={<ReportPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/profile/match/:roleId" element={<MatchDetailPage />} />
          <Route path="/graph" element={<GraphPage />} />
          {/* 旧教练路由已废弃 — 教练现为全局浮动入口 */}
          <Route path="/coach/chat" element={<Navigate to="/" replace />} />
          <Route path="/coach/results" element={<Navigate to="/" replace />} />
          <Route path="/coach/result/:id" element={<Navigate to="/" replace />} />
          <Route path="/roles/:roleId" element={<RoleDetailPage />} />
          <Route path="/growth-log" element={<GrowthLogPage />} />
          <Route path="/growth-log/projects/:id" element={<ProjectGraphPage />} />
          <Route path="/growth-log/pursuits/:id" element={<PursuitDetailPage />} />
          <Route path="/explore" element={<ExplorePage />} />
          <Route path="/interview" element={<InterviewPage />} />
          <Route path="/jd-diagnosis/:id?" element={<JDDiagnosisPage />} />
          <Route path="/report/print/:id" element={<ReportPrintPage />} />
          {/* 旧路由重定向 */}
          <Route path="/growth" element={<Navigate to="/growth-log" replace />} />
          <Route path="/applications" element={<Navigate to="/growth-log" replace />} />
          <Route path="/growth-log-v2" element={<Navigate to="/growth-log" replace />} />
          <Route path="/explore/:nodeId/learning" element={<Navigate to="/growth-log" replace />} />
          <Route path="/profile/learning" element={<Navigate to="/growth-log" replace />} />
          <Route path="/jd" element={<Navigate to="/growth-log" replace />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  </>
  )
}

export default App
