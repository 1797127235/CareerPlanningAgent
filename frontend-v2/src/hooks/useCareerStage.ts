import { useQuery } from '@tanstack/react-query'
import { fetchCareerStage, type CareerStage } from '@/api/user'

export function useCareerStage() {
  return useQuery<{ stage: CareerStage }>({
    queryKey: ['career-stage'],
    queryFn: fetchCareerStage,
    staleTime: 5 * 60 * 1000,  // 5 分钟内不重取
  })
}

// 辅助：默认兜底为 focusing（未加载时避免闪第一屏）
export function useCurrentStage(): CareerStage {
  const { data } = useCareerStage()
  return data?.stage ?? 'focusing'
}

export type { CareerStage }
