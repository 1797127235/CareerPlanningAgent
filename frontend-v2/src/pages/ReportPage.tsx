import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { generateReportV2, type ReportV2Data } from '@/api/report'
import {
  ReportPrologue,
  ReportChapterI,
  ReportChapterII,
  ReportChapterIII,
  ReportChapterIV,
  ReportEpilogue,
} from '@/components/report-v2'
import { mockReportData } from '@/components/report-v2/mockData'
import { TableOfContents } from '@/components/editorial'

const tocItems = [
  { id: 'chapter-1', numeral: 'I', label: '你是谁' },
  { id: 'chapter-2', numeral: 'II', label: '你能去哪' },
  { id: 'chapter-3', numeral: 'III', label: '差距' },
  { id: 'chapter-4', numeral: 'IV', label: '下一步' },
]

export default function ReportPage() {
  const [searchParams] = useSearchParams()
  const isMock = searchParams.get('mock') === '1'

  const [data, setData] = useState<ReportV2Data | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (isMock) {
      setData(mockReportData)
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)
    try {
      const detail = await generateReportV2()
      if (!detail.data || !detail.data.target) {
        setError('报告数据不完整，请稍后重试。')
      } else {
        setData(detail.data)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '请求失败')
    } finally {
      setLoading(false)
    }
  }, [isMock])

  useEffect(() => {
    load()
  }, [load])

  if (loading) {
    return (
      <main className="min-h-screen bg-[var(--bg-paper)] flex items-center justify-center px-6">
        <div className="text-center">
          <p className="font-serif italic text-[length:var(--fs-body-lg)] text-[var(--ink-2)]">
            正在为你写这封信…
          </p>
        </div>
      </main>
    )
  }

  if (error) {
    return (
      <main className="min-h-screen bg-[var(--bg-paper)] flex items-center justify-center px-6">
        <div className="text-center max-w-md">
          <p className="font-sans text-[length:var(--fs-body-lg)] text-[var(--ink-1)]">生成报告时出错了</p>
          <p className="mt-2 text-[length:var(--fs-body)] text-[var(--ink-3)]">{error}</p>
          <button
            onClick={load}
            className="mt-6 inline-flex items-center px-5 py-2.5 rounded-full border border-[var(--line)] text-[var(--ink-1)] hover:bg-[var(--line)]/10 transition-colors text-sm font-medium"
          >
            重试
          </button>
        </div>
      </main>
    )
  }

  if (!data) {
    return (
      <main className="min-h-screen bg-[var(--bg-paper)] flex items-center justify-center px-6">
        <p className="text-[length:var(--fs-body)] text-[var(--ink-3)]">暂无报告数据</p>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-[var(--bg-paper)] text-[var(--ink-1)]">
      <div className="mx-auto max-w-[1180px] px-6 md:px-10 xl:px-14 pt-6 md:pt-10 pb-24 md:pb-28">
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
  )
}
