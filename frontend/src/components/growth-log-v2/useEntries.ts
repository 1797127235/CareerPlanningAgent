import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import {
  listEntries, createEntry, updateEntry, deleteEntry, aiSuggest,
} from '@/api/growthEntries'
import type { GrowthEntry } from './mockData'

const QK = ['growth-entries'] as const

export function useGrowthEntries() {
  const qc = useQueryClient()

  const list = useQuery({
    queryKey: QK,
    queryFn: () => listEntries(),
    staleTime: 30_000,
  })

  const add = useMutation({
    mutationFn: (data: Partial<GrowthEntry>) => createEntry(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: QK }),
  })

  const patch = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<GrowthEntry> }) => updateEntry(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: QK }),
  })

  const remove = useMutation({
    mutationFn: (id: number) => deleteEntry(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: QK }),
  })

  const requestAi = useMutation({
    mutationFn: (id: number) => aiSuggest(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: QK }),
  })

  return {
    entries: list.data?.entries ?? [],
    loading: list.isLoading,
    error: list.error,
    addEntry: add.mutateAsync,
    updateEntry: (id: number, data: Partial<GrowthEntry>) => patch.mutateAsync({ id, data }),
    deleteEntry: remove.mutateAsync,
    requestAiSuggestions: requestAi.mutateAsync,
  }
}
