import { useParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { fetchReportDetail } from '@/api/report'
import type { ReportV2Data } from '@/api/report'
import { useFontsReady } from '@/components/report-print/utils/useFontsReady'
import { PrintHeader } from '@/components/report-print/PrintHeader'
import { PrintChapterI } from '@/components/report-print/PrintChapterI'
import { PrintChapterII } from '@/components/report-print/PrintChapterII'
import { PrintChapterIII } from '@/components/report-print/PrintChapterIII'
import { PrintChapterIV } from '@/components/report-print/PrintChapterIV'
import { PrintFooter } from '@/components/report-print/PrintFooter'

export default function ReportPrintPage() {
  const { id } = useParams<{ id: string }>()
  const [data, setData] = useState<ReportV2Data | null>(null)
  const [loading, setLoading] = useState(true)
  const [layoutFlags, setLayoutFlags] = useState({
    ch1: false,
    ch2: false,
    ch3: false,
    ch4: false,
  })
  const fontsReady = useFontsReady()

  useEffect(() => {
    if (!id) return
    setLoading(true)
    fetchReportDetail(Number(id))
      .then((detail) => {
        const reportData = detail.data as unknown as ReportV2Data
        if (reportData && reportData.target) setData(reportData)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [id])

  // 让打印整张 A4 都是米色——只在本路由下，挂载时改 html/body，卸载时复原
  useEffect(() => {
    const htmlEl = document.documentElement
    const bodyEl = document.body
    const prevHtmlBg = htmlEl.style.background
    const prevBodyBg = bodyEl.style.background
    htmlEl.style.background = '#f7f2e8'
    bodyEl.style.background = '#f7f2e8'
    return () => {
      htmlEl.style.background = prevHtmlBg
      bodyEl.style.background = prevBodyBg
    }
  }, [])

  const ready = data && fontsReady && layoutFlags.ch1 && layoutFlags.ch2 && layoutFlags.ch3 && layoutFlags.ch4 && !loading

  return (
    <div
      className="report-print-root"
      data-print-ready={ready ? 'true' : 'false'}
    >
      {loading && <div className="p-10">Loading...</div>}
      {!loading && data && fontsReady && (
        <>
          <PrintHeader data={data} />
          <PrintChapterI
            data={data}
            onLayoutDone={() =>
              setLayoutFlags((f) => ({ ...f, ch1: true }))
            }
          />
          <PrintChapterII
            data={data}
            onLayoutDone={() =>
              setLayoutFlags((f) => ({ ...f, ch2: true }))
            }
          />
          <PrintChapterIII
            data={data}
            onLayoutDone={() =>
              setLayoutFlags((f) => ({ ...f, ch3: true }))
            }
          />
          <PrintChapterIV
            data={data}
            onLayoutDone={() =>
              setLayoutFlags((f) => ({ ...f, ch4: true }))
            }
          />
          <PrintFooter data={data} />
        </>
      )}
      {!loading && !data && (
        <div className="p-10 text-red-600">无法加载报告数据</div>
      )}
    </div>
  )
}
