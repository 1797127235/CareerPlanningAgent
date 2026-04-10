import { rawFetch } from '@/api/client'
import type { DiagnoseRequest, DiagnoseResult } from '@/types/jd'

export async function diagnoseJd(req: DiagnoseRequest): Promise<DiagnoseResult> {
  return rawFetch<DiagnoseResult>('/jd/diagnose', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}
