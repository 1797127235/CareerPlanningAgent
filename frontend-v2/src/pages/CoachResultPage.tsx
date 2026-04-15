import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getCoachResult } from '@/api/coach'
import { TableOfContents } from '@/components/editorial'
import {
  CoachResultPrologue,
  JdDiagnosisChapters,
  MarkdownNarrativeView,
  CoachResultEpilogue,
} from '@/components/coach-v2'
import { mockJdDiagnosis, mockCareerReport, mockInterviewReview } from '@/components/coach-v2/mockData'
import { bucketOf } from '@/lib/resultTypeBuckets'
import type { CoachResultDetail } from '@/types/coach'

function useCoachResult(id: string | undefined, isMock: boolean, mockData: CoachResultDetail | null) {
  return useQuery<CoachResultDetail>({
    queryKey: ['coach-result', id],
    queryFn: () => getCoachResult(Number(id)),
    enabled: !!id && !isMock,
    initialData: isMock && mockData ? mockData : undefined,
  })
}

export default function CoachResultPage() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const isMock = searchParams.get('mock') === '1'
  const mockType = searchParams.get('type') || 'jd'

  const mockData = isMock
    ? mockType === 'narrative'
      ? mockCareerReport
      : mockType === 'review'
        ? mockInterviewReview
        : mockJdDiagnosis
    : null

  const { data, isLoading, error } = useCoachResult(id, isMock, mockData)

  if (isLoading) {
    return (
      <main className="min-h-screen bg-[var(--bg-paper)] flex items-center justify-center px-6">
        <p className="font-serif italic text-[length:var(--fs-body-lg)] text-[var(--ink-2)]">
          正在打开分析结果…
        </p>
      </main>
    )
  }

  if (error || !data) {
    return (
      <main className="min-h-screen bg-[var(--bg-paper)] flex items-center justify-center px-6">
        <div className="text-center max-w-md">
          <p className="font-sans text-[length:var(--fs-body-lg)] text-[var(--ink-1)]">结果加载失败</p>
          <p className="mt-2 text-[length:var(--fs-body)] text-[var(--ink-3)]">
            {error instanceof Error ? error.message : '找不到这份分析结果'}
          </p>
          <button
            onClick={() => navigate(-1)}
            className="mt-6 inline-flex items-center px-5 py-2.5 rounded-full border border-[var(--line)] text-[var(--ink-1)] hover:bg-[var(--line)]/10 transition-colors text-sm font-medium"
          >
            返回
          </button>
        </div>
      </main>
    )
  }

  const isStructured = !!data.detail?._structured
  const bucket = bucketOf(data.result_type, isStructured)

  const tocItems =
    bucket === 'diagnosis'
      ? [
          { id: 'chapter-1', numeral: 'I', label: '准备度' },
          { id: 'chapter-2', numeral: 'II', label: '已具备' },
          { id: 'chapter-3', numeral: 'III', label: '缺口' },
          { id: 'chapter-4', numeral: 'IV', label: '下一步' },
        ]
      : [{ id: 'chapter-1', numeral: 'I', label: '全文' }]

  return (
    <main className="min-h-screen bg-[var(--bg-paper)] text-[var(--ink-1)]">
      <div className="max-w-[720px] mx-auto px-6 md:px-12 lg:px-20 pb-32">
        <CoachResultPrologue data={data} />
        <div id="chapter-1">
          {bucket === 'diagnosis' ? (
            <JdDiagnosisChapters data={data} />
          ) : (
            <MarkdownNarrativeView data={data} />
          )}
        </div>
        <CoachResultEpilogue data={data} />
      </div>
      <TableOfContents items={tocItems} />
    </main>
  )
}
