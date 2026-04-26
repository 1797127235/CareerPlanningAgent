import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ToastProvider } from '@/components/ui'
import HomePage from './pages/HomePage'
import DemoPage from './pages/DemoPage'
import ReportPage from './pages/ReportPage'
import ProfilePage from './pages/ProfilePage'
import LoginPage from './pages/LoginPage'
import CoachResultPage from './pages/CoachResultPage'
import CoachResultsListPage from './pages/CoachResultsListPage'
import CoachChatPage from './pages/CoachChatPage'
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

function App() {
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const theme = params.get('theme')
    if (theme === 'night') document.documentElement.setAttribute('data-theme', 'night')
    else document.documentElement.removeAttribute('data-theme')
  }, [])

  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/__demo" element={<DemoPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/report" element={<ReportPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/profile/match/:roleId" element={<MatchDetailPage />} />
          <Route path="/graph" element={<GraphPage />} />
          <Route path="/coach/chat" element={<CoachChatPage />} />
          <Route path="/coach/results" element={<CoachResultsListPage />} />
          <Route path="/coach/result/:id" element={<CoachResultPage />} />
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
  )
}

export default App
