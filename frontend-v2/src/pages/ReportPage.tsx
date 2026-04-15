import { useEffect, useState } from 'react'
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

export default function ReportPage() {
  const [searchParams] = useSearchParams()
  const isMock = searchParams.get('mock') === '1'

  const [data, setData] = useState<ReportV2Data | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
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
  }

  useEffect(() => {
    load()
  }, [isMock])

  if (loading) {
    return (
      <main className="min-h-screen bg-[var(--bg-paper)] flex items-center justify-center px-6">
        <div className="text-center">
          <p className="font-serif italic text-[var(--fs-body-lg)] text-[var(--ink-2)]">
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
          <p className="font-sans text-[var(--fs-body-lg)] text-[var(--ink-1)]">生成报告时出错了</p>
          <p className="mt-2 text-[var(--fs-body)] text-[var(--ink-3)]">{error}</p>
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
        <p className="text-[var(--fs-body)] text-[var(--ink-3)]">暂无报告数据</p>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-[var(--bg-paper)] text-[var(--ink-1)]">
      <div className="max-w-[900px] mx-auto px-6 md:px-16 lg:px-32 pb-32">
        <ReportPrologue targetLabel={data.target.label} />
        <ReportChapterI data={data} />
        <ReportChapterII data={data} />
        <ReportChapterIII data={data} />
        <ReportChapterIV data={data} />
        <ReportEpilogue generatedAt={data.generated_at} />
      </div>
    </main>
  )
}
