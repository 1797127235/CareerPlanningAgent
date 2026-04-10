import { useQuery } from '@tanstack/react-query'
import { rawFetch } from '@/api/client'

export interface Guidance {
  stage: string
  message: string
  cta_text: string
  cta_route: string
  tone: string
}

export function useGuidance(page: string) {
  return useQuery<Guidance>({
    queryKey: ['guidance', page],
    queryFn: () => rawFetch(`/guidance?page=${page}`),
    staleTime: 0,           // always refetch on mount — guidance is context-sensitive
    refetchOnWindowFocus: true,
  })
}
