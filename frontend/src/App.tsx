import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import HomePage from '@/pages/HomePage'
import ProfilePage from '@/pages/ProfilePage'
import MatchDetailPage from '@/pages/MatchDetailPage'
import GraphPage from '@/pages/GraphPage'
import ReportPage from '@/pages/ReportPage'
import GrowthLogPage from '@/pages/GrowthLogPage'
import CoachResultPage from '@/pages/CoachResultPage'
import LearningPage from '@/pages/LearningPage'
import LearningPathPage from '@/pages/LearningPathPage'
import RoleDetailPage from '@/pages/RoleDetailPage'
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
          <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<HomePage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/roles/:roleId" element={<RoleDetailPage />} />
            <Route path="/profile/match/:roleId" element={<MatchDetailPage />} />
            <Route path="/graph" element={<GraphPage />} />
            <Route path="/explore/:nodeId/learning" element={<LearningPage />} />
            <Route path="/profile/learning" element={<LearningPathPage />} />
            <Route path="/jd" element={<Navigate to="/growth-log?tab=pursuits" replace />} />
            <Route path="/growth" element={<Navigate to="/growth-log" replace />} />
            <Route path="/applications" element={<Navigate to="/growth-log?tab=pursuits" replace />} />
            <Route path="/report" element={<ReportPage />} />
            <Route path="/growth-log" element={<GrowthLogPage />} />
            <Route path="/coach/result/:id" element={<CoachResultPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
