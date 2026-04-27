import { useCallback, useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Trash2, Loader2, FileText } from 'lucide-react'
import { fetchReportDetail, generateReportV2, deleteReport } from '@/api/report'
import type { ReportV2Data } from '@/api/report'
import {
  ReportPrologue,
  ReportChapterI,
  ReportChapterII,
  ReportChapterIII,
  ReportChapterIV,
  ReportEpilogue,
} from '@/components/report-v2'
import { TableOfContents, ReadingProgressBar } from '@/components/editorial'
import Navbar from '@/components/shared/Navbar'

const tocItems = [
  { id: 'chapter-1', numeral: 'I', label: '你是谁' },
  { id: 'chapter-2', numeral: 'II', label: '你能去哪' },
  { id: 'chapter-3', numeral: 'III', label: '差距' },
  { id: 'chapter-4', numeral: 'IV', label: '下一步' },
]

export default function ReportPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const reportId = id ? parseInt(id, 10) : null

  const [regenerating, setRegenerating] = useState(false)

  const {
    data: detail,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['report', reportId],
    queryFn: () => fetchReportDetail(reportId!),
    enabled: !!reportId,
    staleTime: 60_000,
  })

  const deleteMut = useMutation({
    mutationFn: () => deleteReport(reportId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reports'] })
      navigate('/report')
    },
  })

  const handleRegenerate = async () => {
    if (!confirm('重新生成将基于你最新的画像数据，是否继续？')) return
    setRegenerating(true)
    try {
      const newDetail = await generateReportV2()
      if (newDetail.data?.target) {
        navigate(`/report/${newDetail.id}`, { replace: true })
        qc.invalidateQueries({ queryKey: ['reports'] })
      }
    } catch (e) {
      alert(e instanceof Error ? e.message : '生成失败')
    } finally {
      setRegenerating(false)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[var(--bg-paper)]">
        <Navbar />
        <main className="min-h-screen flex items-center justify-center px-6 pt-[64px]">
          <div className="text-center">
            <Loader2 className="w-6 h-6 animate-spin text-[var(--ink-3)] mx-auto mb-3" />
            <p className="font-serif italic text-[length:var(--fs-body-lg)] text-[var(--ink-2)]">
              正在加载报告…
            </p>
          </div>
        </main>
      </div>
    )
  }

  if (error || !detail) {
    return (
      <div className="min-h-screen bg-[var(--bg-paper)]">
        <Navbar />
        <main className="min-h-screen flex items-center justify-center px-6 pt-[64px]">
          <div className="text-center max-w-md">
            <FileText className="w-10 h-10 text-[var(--line)] mx-auto mb-4" />
            <p className="font-sans text-[length:var(--fs-body-lg)] text-[var(--ink-1)]">
              报告不存在或已删除
            </p>
            <button
              onClick={() => navigate('/report')}
              className="mt-6 inline-flex items-center gap-1.5 px-5 py-2.5 rounded-full border border-[var(--line)] text-[var(--ink-1)] hover:bg-[var(--line)]/10 transition-colors text-sm font-medium cursor-pointer"
            >
              <ArrowLeft className="w-4 h-4" />
              返回报告列表
            </button>
          </div>
        </main>
      </div>
    )
  }

  const data = detail.data as ReportV2Data | undefined

  if (!data?.target) {
    return (
      <div className="min-h-screen bg-[var(--bg-paper)]">
        <Navbar />
        <main className="min-h-screen flex items-center justify-center px-6 pt-[64px]">
          <div className="text-center max-w-md">
            <p className="font-sans text-[length:var(--fs-body-lg)] text-[var(--ink-1)]">报告数据不完整</p>
            <button
              onClick={() => navigate('/report')}
              className="mt-6 inline-flex items-center px-5 py-2.5 rounded-full border border-[var(--line)] text-[var(--ink-1)] hover:bg-[var(--line)]/10 transition-colors text-sm font-medium cursor-pointer"
            >
              返回报告列表
            </button>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[var(--bg-paper)] text-[var(--ink-1)]">
      <ReadingProgressBar />
      <Navbar />
      <main className="pt-[80px] pb-24 md:pb-28">
        <div className="mx-auto max-w-[1180px] px-6 md:px-10 xl:px-14">
        {/* Top bar */}
        <div className="flex items-center justify-between mb-8">
          <button
            onClick={() => navigate('/report')}
            className="inline-flex items-center gap-1.5 text-[13px] font-medium text-[var(--ink-3)] hover:text-[var(--ink-1)] transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
            返回列表
          </button>
          <div className="flex items-center gap-2">
            <button
              onClick={handleRegenerate}
              disabled={regenerating}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full border border-[var(--line)] text-[13px] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)] hover:bg-[var(--line)]/10 transition-colors disabled:opacity-50 cursor-pointer"
            >
              {regenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
              {regenerating ? '生成中…' : '重新生成'}
            </button>
            <button
              onClick={() => {
                if (confirm('确定删除这份报告？')) deleteMut.mutate()
              }}
              disabled={deleteMut.isPending}
              className="p-2 rounded-full text-[var(--ink-3)] hover:text-red-500 hover:bg-red-50 transition-colors cursor-pointer"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,780px)_180px] xl:grid-cols-[minmax(0,820px)_190px] gap-10 lg:gap-12 xl:gap-16 items-start">
          <div className="min-w-0">
            <ReportPrologue targetLabel={data.target.label} />
            <div id="chapter-1"><ReportChapterI data={data} /></div>
            <div id="chapter-2"><ReportChapterII data={data} /></div>
            <div id="chapter-3"><ReportChapterIII data={data} /></div>
            <div id="chapter-4"><ReportChapterIV data={data} /></div>
            <ReportEpilogue generatedAt={data.generated_at} />
          </div>
          <aside className="hidden lg:block">
            <TableOfContents placement="inline" className="sticky top-24" items={tocItems} />
          </aside>
        </div>
      </div>
    </main>
  </div>
  )
}
