import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { analyzeAnswer, fetchPracticeHistory, deletePracticeRecord } from '@/api/practice'
import type { AnalyzeRequest } from '@/types/practice'

export function usePracticeAnalyzeMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (req: AnalyzeRequest) => analyzeAnswer(req),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['practice-history'] })
      queryClient.invalidateQueries({ queryKey: ['guidance'] })
    },
  })
}

export function usePracticeHistoryQuery() {
  return useQuery({
    queryKey: ['practice-history'],
    queryFn: fetchPracticeHistory,
  })
}

export function usePracticeDeleteMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => deletePracticeRecord(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['practice-history'] })
    },
  })
}
