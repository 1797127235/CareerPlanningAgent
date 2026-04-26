import { useLayoutEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchGraphMap } from '@/api/graph'
import { fetchProfile } from '@/api/profiles'
import { Coverflow } from '@/components/explorer/Coverflow'
import Navbar from '@/components/shared/Navbar'
import type { GraphNode } from '@/types/graph'
import type { ProfileData } from '@/types/profile'

/* ── Mocks ── */
const mockNodes: GraphNode[] = [
  { node_id: 'fe-junior', label: '前端开发实习生', role_family: '前端开发', zone: 'safe', replacement_pressure: 0.2, human_ai_leverage: 0.3, salary_p50: 8000, career_level: 1, must_skills: ['HTML', 'CSS', 'JavaScript'], skill_count: 40, degree: 6 },
  { node_id: 'fe-mid', label: '前端开发工程师', role_family: '前端开发', zone: 'safe', replacement_pressure: 0.3, human_ai_leverage: 0.4, salary_p50: 18000, career_level: 2, must_skills: ['React', 'TypeScript', 'Webpack'], skill_count: 75, degree: 8 },
  { node_id: 'fe-senior', label: '高级前端工程师', role_family: '前端开发', zone: 'leverage', replacement_pressure: 0.4, human_ai_leverage: 0.7, salary_p50: 32000, career_level: 3, must_skills: ['Performance', 'Architecture', 'Leadership'], skill_count: 110, degree: 10 },
  { node_id: 'fe-staff', label: '前端架构师', role_family: '前端开发', zone: 'leverage', replacement_pressure: 0.5, human_ai_leverage: 0.8, salary_p50: 50000, career_level: 4, must_skills: ['System Design', 'Cross-team', 'Strategy'], skill_count: 140, degree: 12 },
  { node_id: 'be-junior', label: '后端开发实习生', role_family: '后端开发', zone: 'transition', replacement_pressure: 0.4, human_ai_leverage: 0.3, salary_p50: 8500, career_level: 1, must_skills: ['Java', 'SQL', 'Spring'], skill_count: 45, degree: 7 },
  { node_id: 'be-mid', label: '后端开发工程师', role_family: '后端开发', zone: 'transition', replacement_pressure: 0.5, human_ai_leverage: 0.4, salary_p50: 19000, career_level: 2, must_skills: ['Redis', 'Kafka', 'Microservices'], skill_count: 85, degree: 9 },
  { node_id: 'algo-mid', label: '算法工程师', role_family: 'AI/ML', zone: 'leverage', replacement_pressure: 0.35, human_ai_leverage: 0.85, salary_p50: 35000, career_level: 3, must_skills: ['Deep Learning', 'Python', 'Math'], skill_count: 120, degree: 8 },
  { node_id: 'pm-mid', label: '产品经理', role_family: '产品', zone: 'danger', replacement_pressure: 0.7, human_ai_leverage: 0.3, salary_p50: 16000, career_level: 2, must_skills: ['Data Analysis', 'User Research', 'Roadmap'], skill_count: 60, degree: 5 },
]

const mockProfile: ProfileData = {
  id: 1,
  name: '林小北',
  source: 'resume',
  created_at: '2024-09-01T10:00:00Z',
  updated_at: '2025-01-15T08:30:00Z',
  profile: {},
  quality: {},
  graph_position: {
    from_node_id: 'fe-mid',
    from_node_label: '前端开发工程师',
    target_node_id: 'fe-senior',
    target_label: '高级前端工程师',
    target_zone: 'leverage',
    gap_skills: ['Performance', 'Architecture'],
    total_hours: 1200,
    safety_gain: 0.35,
    salary_p50: 32000,
  },
  career_goals: [],
}

/* ── Main Page ── */
export default function GraphPage() {
  const [isMock] = useState(() => new URLSearchParams(window.location.search).get('mock') === '1')

  useLayoutEffect(() => {
    const html = document.documentElement
    const body = document.body
    const previousHtmlOverflow = html.style.overflow
    const previousBodyOverflow = body.style.overflow
    const previousBodyOverscroll = body.style.overscrollBehavior

    window.scrollTo({ top: 0, left: 0, behavior: 'auto' })
    html.style.overflow = 'hidden'
    body.style.overflow = 'hidden'
    body.style.overscrollBehavior = 'none'

    return () => {
      html.style.overflow = previousHtmlOverflow
      body.style.overflow = previousBodyOverflow
      body.style.overscrollBehavior = previousBodyOverscroll
    }
  }, [])

  const mapQ = useQuery({
    queryKey: ['graph-map'],
    queryFn: fetchGraphMap,
    enabled: !isMock,
    initialData: isMock ? { nodes: mockNodes, edges: [], node_count: mockNodes.length, edge_count: 0 } : undefined,
  })

  const profileQ = useQuery({
    queryKey: ['profile'],
    queryFn: fetchProfile,
    enabled: !isMock,
    initialData: isMock ? mockProfile : undefined,
  })

  const nodes = mapQ.data?.nodes ?? []
  const gp = profileQ.data?.graph_position
  const fromNodeId = gp?.from_node_id ?? undefined
  const targetNodeId = gp?.target_node_id !== gp?.from_node_id ? (gp?.target_node_id ?? undefined) : undefined
  const careerGoals = profileQ.data?.career_goals ?? []

  const hasRealProfile = !!(
    profileQ.data?.name?.trim() ||
    (profileQ.data?.profile && Object.keys(profileQ.data.profile).length > 0)
  )
  const profileId = hasRealProfile ? (profileQ.data?.id ?? undefined) : undefined

  if (mapQ.isLoading) {
    return (
      <main className="min-h-screen bg-[var(--bg-paper)] flex items-center justify-center px-[var(--space-5)]">
        <p className="font-serif italic text-[var(--text-lg)] text-[var(--ink-2)]">正在绘制图谱…</p>
      </main>
    )
  }

  if (mapQ.error || nodes.length === 0) {
    return (
      <main className="min-h-screen bg-[var(--bg-paper)] flex items-center justify-center px-[var(--space-5)]">
        <div className="text-center max-w-md">
          <p className="text-[var(--text-lg)] text-[var(--ink-1)]">图谱加载失败</p>
          <p className="mt-2 text-[var(--text-base)] text-[var(--ink-3)]">{mapQ.error instanceof Error ? mapQ.error.message : '暂无数据'}</p>
        </div>
      </main>
    )
  }

  return (
    <>
      <Navbar />
      <main className="mt-[64px] h-[calc(100vh-64px)] bg-[var(--bg-paper)] text-[var(--ink-1)] overflow-hidden">
        <Coverflow
          nodes={nodes}
          edges={mapQ.data?.edges ?? []}
          profileId={profileId}
          fromNodeId={fromNodeId}
          targetNodeId={targetNodeId}
          careerGoals={careerGoals}
          onGoalSet={() => profileQ.refetch()}
        />
      </main>
    </>
  )
}
