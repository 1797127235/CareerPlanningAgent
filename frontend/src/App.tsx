import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import HomePage from '@/pages/HomePage'
import ProfilePage from '@/pages/ProfilePage'
import MatchDetailPage from '@/pages/MatchDetailPage'
import GraphPage from '@/pages/GraphPage'
import ReportPage from '@/pages/ReportPage'
import ReportPrintPage from '@/pages/ReportPrintPage'
import GrowthLogV2Page from '@/pages/GrowthLogV2Page'
import ProjectGraphPage from '@/pages/ProjectGraphPage'
import PursuitDetailPage from '@/pages/PursuitDetailPage'
import CoachResultPage from '@/pages/CoachResultPage'
import InterviewPage from '@/pages/InterviewPage'
import JDDiagnosisPage from '@/pages/JDDiagnosisPage'
import RoleDetailPage from '@/pages/RoleDetailPage'
import ExplorePage from '@/pages/ExplorePage'
import LoginPage from '@/pages/LoginPage'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { Layout } from '@/components/Layout'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="bg-canvas" />
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/report/print/:id" element={<ReportPrintPage />} />
          <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<HomePage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/roles/:roleId" element={<RoleDetailPage />} />
            <Route path="/profile/match/:roleId" element={<MatchDetailPage />} />
            <Route path="/graph" element={<GraphPage />} />
            <Route path="/explore" element={<ExplorePage />} />
            {/* 学习路径已砍 — 旧路由重定向到成长档案，保证外部链接不 404 */}
            <Route path="/explore/:nodeId/learning" element={<Navigate to="/growth-log" replace />} />
            <Route path="/profile/learning" element={<Navigate to="/growth-log" replace />} />
            <Route path="/jd" element={<Navigate to="/growth-log" replace />} />
            <Route path="/growth" element={<Navigate to="/growth-log" replace />} />
            <Route path="/applications" element={<Navigate to="/growth-log" replace />} />
            <Route path="/report" element={<ReportPage />} />
            <Route path="/growth-log" element={<GrowthLogV2Page />} />
            <Route path="/growth-log-v2" element={<Navigate to="/growth-log" replace />} />
            <Route path="/growth-log/projects/:id" element={<ProjectGraphPage />} />
            <Route path="/growth-log/pursuits/:id" element={<PursuitDetailPage />} />
            <Route path="/coach/result/:id" element={<CoachResultPage />} />
            <Route path="/interview" element={<InterviewPage />} />
            <Route path="/jd-diagnosis/:id?" element={<JDDiagnosisPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
