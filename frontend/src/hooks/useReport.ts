import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchReportList, fetchReportDetail, generateReport, deleteReport, editReport, polishReport } from '@/api/report'

export function useReportListQuery() {
  return useQuery({
    queryKey: ['report-list'],
    queryFn: () => fetchReportList(),
  })
}

export function useReportDetailQuery(reportId: number | null) {
  return useQuery({
    queryKey: ['report-detail', reportId],
    queryFn: () => fetchReportDetail(reportId!),
    enabled: reportId !== null,
  })
}

export function useGenerateReportMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => generateReport(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['report-list'] })
      queryClient.invalidateQueries({ queryKey: ['guidance'] })
    },
  })
}

export function useDeleteReportMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (reportId: number) => deleteReport(reportId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['report-list'] })
    },
  })
}

export function useEditReportMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ reportId, edits }: { reportId: number; edits: { narrative_summary?: string; chapter_narratives?: Record<string, string> } }) =>
      editReport(reportId, edits),
    onSuccess: (_, { reportId }) => {
      queryClient.invalidateQueries({ queryKey: ['report-detail', reportId] })
    },
  })
}

export function usePolishReportMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (reportId: number) => polishReport(reportId),
    onSuccess: (_, reportId) => {
      queryClient.invalidateQueries({ queryKey: ['report-detail', reportId] })
    },
  })
}
