import { useSearchParams } from 'react-router-dom'
import { useGraphMapQuery } from '@/hooks/useGraph'
import { useAuth } from '@/hooks/useAuth'
import { useProfileData } from '@/hooks/useProfileData'
import { EmptyState } from '@/components/shared'
import { Coverflow } from '@/components/explorer/Coverflow'

export default function GraphPage() {
  const [searchParams] = useSearchParams()
  const initialNodeId = searchParams.get('node') || undefined
  const { data: mapData, isLoading, isError } = useGraphMapQuery()

  const { token } = useAuth()
  const { profile, loadProfile } = useProfileData(token)

  // Only treat a profile as "real" if it has at least a name or some skills.
  // An auto-created empty profile record must not unlock goal-setting UI.
  const hasRealProfile = !!(
    profile?.name?.trim() ||
    (profile?.profile?.skills?.length ?? 0) > 0
  )
  const profileId = hasRealProfile ? (profile?.id ?? undefined) : undefined
  const gp = profile?.graph_position
  const fromNodeId = gp?.from_node_id ?? undefined
  const targetNodeId = gp?.target_node_id !== gp?.from_node_id ? (gp?.target_node_id ?? undefined) : undefined
  const careerGoals = profile?.career_goals ?? []

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-[var(--blue)] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-[14px] text-slate-500">正在加载岗位数据...</p>
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center h-full px-8">
        <EmptyState icon="🗺️" title="数据加载失败" description="请检查网络连接后重试" ctaText="刷新页面" ctaHref="/graph" />
      </div>
    )
  }

  if (mapData && mapData.nodes.length > 0) {
    return (
      <div className="h-full flex flex-col">
        <div className="flex-1 min-h-0">
          <Coverflow
            nodes={mapData.nodes}
            edges={mapData.edges ?? []}
            initialNodeId={initialNodeId}
            profileId={profileId}
            fromNodeId={fromNodeId}
            targetNodeId={targetNodeId}
            careerGoals={careerGoals}
            onGoalSet={loadProfile}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center h-full px-8">
      <EmptyState icon="🗺️" title="暂无岗位数据" description="系统正在构建岗位数据，请稍后再来" ctaText="返回首页" ctaHref="/" />
    </div>
  )
}
