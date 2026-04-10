import { useQuery } from '@tanstack/react-query'
import { fetchGraphMap } from '@/api/graph'

export function useGraphMapQuery() {
  return useQuery({
    queryKey: ['graph-map'],
    queryFn: fetchGraphMap,
    staleTime: 5 * 60 * 1000, // 5 min — graph data rarely changes
  })
}
