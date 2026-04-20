/**
 * ReportPage — v2 narrative structure rendered with v1 editorial language.
 *
 * Flow:
 *   - Mount: fast path via fetchReportList + fetchReportDetail (ms).
 *   - Slow POST /report/generate runs only on explicit "开始写" / "再生成".
 *   - GeneratingScreen rotates progressive copy during long waits.
 *   - HistoryStrip (always visible below Prologue) lets the user switch past
 *     reports and delete them (optimistic + 4.5s undo toast).
 *   - ChapterI exposes inline narrative edit → editReport(narrative_summary).
 *   - Epilogue exposes "AI 润色" → polishReport → refetch detail.
 */
import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  generateReportV2,
  fetchReportList,
  fetchReportDetail,
  fetchReportStatus,
  editReport,
  deleteReport,
  exportReportPdf,
  polishReport,
  type ReportV2Data,
  type ReportListItem,
} from '@/api/report'
import {
  ChapterI,
  ChapterII,
  ChapterIII,
  ChapterIV,
  Epilogue,
  TableOfContents,
} from '@/components/report'
import { ToastContainer, type ToastState } from '@/components/shared/Toast'

function LoadingDots() {
  const [n, setN] = useState(0)
  useEffect(() => {
    const id = window.setInterval(() => setN((v) => (v + 1) % 4), 420)
    return () => window.clearInterval(id)
  }, [])
  return <span className="inline-block w-6 text-left tabular-nums">{'.'.repeat(n)}</span>
}

const NEEDS_GOAL_PATTERN = /设定.*(目标|方向)|岗位图谱|先(选|选择|选定).*(目标|方向)/

const GENERATING_MESSAGES = [
  '正在读你的档案',
  '对齐目标方向',
  '比较你和方向的差距',
  '写第一章 · 你是谁',
  '写第二章 · 你能去哪',
  '写第三章 · 差距',
  '写第四章 · 下一步',
  '整理行动清单',
  '快好了',
]

function GeneratingScreen() {
  const [idx, setIdx] = useState(0)
  useEffect(() => {
    const id = window.setInterval(() => {
      setIdx((i) => Math.min(i + 1, GENERATING_MESSAGES.length - 1))
    }, 3500)
    return () => window.clearInterval(id)
  }, [])
  return (
    <main className="min-h-screen flex items-center justify-center px-6">
      <div className="text-center max-w-md">
        <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-slate-400 mb-3">
          职业生涯发展报告
        </p>
        <p className="text-[28px] md:text-[32px] font-bold text-slate-900 tracking-tight leading-[1.2]">
          {GENERATING_MESSAGES[idx]}
          <LoadingDots />
        </p>
        <p className="mt-4 text-[13px] text-slate-500 max-w-[36ch] mx-auto leading-relaxed">
          AI 在写这一份，大概需要几分钟。
        </p>
        {idx >= 4 && (
          <p className="mt-2 text-[13px] text-slate-400 max-w-[36ch] mx-auto leading-relaxed">
            你可以切个窗口忙别的，写完了会留在这里。
          </p>
        )}
      </div>
    </main>
  )
}

export default function ReportPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const isMock = searchParams.get('mock') === '1'
  void isMock

  const [data, setData] = useState<ReportV2Data | null>(null)
  const [reportList, setReportList] = useState<ReportListItem[]>([])
  const [currentId, setCurrentId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [switchingTo, setSwitchingTo] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [toast, setToast] = useState<ToastState | null>(null)
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)

  // Deferred delete: optimistically hide from list, commit to server after 4.5s
  // unless the user hits undo.
  const pendingDeleteRef = useRef<{
    id: number
    timer: number
    prevList: ReportListItem[]
  } | null>(null)

  const pollIntervalRef = useRef<number | null>(null)

  const stopPoll = () => {
    if (pollIntervalRef.current != null) {
      window.clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }

  const loadInitial = async () => {
    setLoading(true)
    setError(null)
    try {
      const list = await fetchReportList()
      setReportList(list)
      if (list.length === 0) return
      const latest = list[0]
      setCurrentId(latest.id)
      const detail = await fetchReportDetail(latest.id)
      const reportData = detail.data as unknown as ReportV2Data
      if (reportData && reportData.target) setData(reportData)
    } catch (e) {
      setError(e instanceof Error ? e.message : '请求失败')
    } finally {
      setLoading(false)
    }
  }

  const switchReport = async (id: number) => {
    if (id === currentId) return
    setSwitchingTo(id)
    setError(null)
    try {
      const detail = await fetchReportDetail(id)
      const reportData = detail.data as unknown as ReportV2Data
      if (reportData && reportData.target) {
        setData(reportData)
        setCurrentId(id)
        window.scrollTo({ top: 0, behavior: 'smooth' })
      } else {
        setError('这份报告的数据不完整。')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '请求失败')
    } finally {
      setSwitchingTo(null)
    }
  }

  // Poll backend /report/status until it reports generating=false, then
  // refetch list + detail so the new report appears. Used on mount to recover
  // from the case where the user navigated away mid-generation.
  const startStatusPoll = () => {
    if (pollIntervalRef.current != null) return
    pollIntervalRef.current = window.setInterval(async () => {
      try {
        const { generating: stillGenerating } = await fetchReportStatus()
        if (!stillGenerating) {
          stopPoll()
          setGenerating(false)
          try {
            const list = await fetchReportList()
            setReportList(list)
            if (list[0]) {
              setCurrentId(list[0].id)
              const detail = await fetchReportDetail(list[0].id)
              const rd = detail.data as unknown as ReportV2Data
              if (rd && rd.target) setData(rd)
            }
          } catch {
            /* non-fatal：下一次 mount 会重试 */
          }
        }
      } catch {
        /* 网络抖动：忽略本次 tick，下一次继续 */
      }
    }, 3000)
  }

  const generate = async () => {
    setGenerating(true)
    setError(null)
    try {
      const detail = await generateReportV2()
      if (!detail.data || !detail.data.target) {
        setError('报告数据不完整，请稍后重试。')
      } else {
        setData(detail.data)
        try {
          const newList = await fetchReportList()
          setReportList(newList)
          if (newList[0]) setCurrentId(newList[0].id)
        } catch {
          /* non-fatal */
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '请求失败')
    } finally {
      setGenerating(false)
    }
  }

  const handleExport = async () => {
    if (exporting || currentId == null) return
    setExporting(true)
    setExportError(null)
    try {
      const blob = await exportReportPdf(currentId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const target = data.target?.label || '报告'
      const date = new Date().toISOString().slice(0, 10)
      a.download = `${target}_职业报告_${date}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e) {
      setExportError(e instanceof Error ? e.message : String(e))
    } finally {
      setExporting(false)
    }
  }


  // Save edited chapter prose. Key "narrative" targets Chapter I (the flat
  // narrative field, via narrative_summary). Any other key targets
  // chapter_narratives[key] as a user override — chapters read this in
  // preference to the AI-generated source text.
  const saveChapter = async (key: string, newText: string) => {
    if (currentId == null) throw new Error('missing report id')
    setSaving(true)
    try {
      if (key === 'narrative') {
        setData((prev) => (prev ? { ...prev, narrative: newText } : prev))
        await editReport(currentId, { narrative_summary: newText })
      } else {
        setData((prev) => {
          if (!prev) return prev
          const nextOverrides = { ...(prev.chapter_narratives ?? {}), [key]: newText }
          return { ...prev, chapter_narratives: nextOverrides }
        })
        await editReport(currentId, { chapter_narratives: { [key]: newText } })
      }
      setToast({ message: '已保存', type: 'success', durationMs: 2000 })
    } catch (e) {
      setToast({
        message: e instanceof Error ? e.message : '保存失败',
        type: 'error',
        durationMs: 4000,
      })
      throw e
    } finally {
      setSaving(false)
    }
  }

  // Deferred delete with undo. Any already-pending delete commits immediately
  // when a new one starts so we don't stack commit timers.
  const stageDelete = (item: ReportListItem) => {
    const prev = pendingDeleteRef.current
    if (prev) {
      window.clearTimeout(prev.timer)
      // commit the previous deletion immediately
      deleteReport(prev.id).catch(() => {})
      pendingDeleteRef.current = null
    }

    const snapshot = reportList
    setReportList((list) => list.filter((r) => r.id !== item.id))

    // If the deleted one was currently viewed, switch to the next latest
    // optimistically (or clear the view if that was the only report).
    if (item.id === currentId) {
      const remaining = snapshot.filter((r) => r.id !== item.id)
      if (remaining[0]) {
        setCurrentId(remaining[0].id)
        fetchReportDetail(remaining[0].id)
          .then((d) => {
            const rd = d.data as unknown as ReportV2Data
            if (rd && rd.target) setData(rd)
          })
          .catch(() => {})
      } else {
        setCurrentId(null)
        setData(null)
      }
    }

    const timer = window.setTimeout(async () => {
      try {
        await deleteReport(item.id)
      } catch {
        // roll back list if the server delete fails
        setReportList(snapshot)
        setToast({ message: '删除失败，已恢复', type: 'error', durationMs: 4000 })
      } finally {
        pendingDeleteRef.current = null
      }
    }, 4500)

    pendingDeleteRef.current = { id: item.id, timer, prevList: snapshot }

    const date = new Date(item.created_at).toISOString().slice(0, 10)
    setToast({
      message: `已删除「${date}」的报告`,
      type: 'info',
      durationMs: 4500,
      action: {
        label: '撤销',
        onClick: () => {
          const pending = pendingDeleteRef.current
          if (!pending) return
          window.clearTimeout(pending.timer)
          setReportList(pending.prevList)
          // If we had swapped currentId optimistically, swap it back too.
          if (item.id !== currentId) {
            // currentId may have been set to the next latest when it matched.
            // Restoring to `item.id` only if the deleted item WAS the current view.
          }
          pendingDeleteRef.current = null
        },
      },
    })
  }

  useEffect(() => {
    loadInitial()
    fetchReportStatus()
      .then(({ generating: isGen }) => {
        if (isGen) {
          setGenerating(true)
          startStatusPoll()
        }
      })
      .catch(() => {
        /* 失败就当没在生成，用户可以手动再点一次 */
      })
    return () => {
      stopPoll()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center px-6">
        <p className="text-[13px] text-slate-400">
          正在读你的档案本
          <LoadingDots />
        </p>
      </main>
    )
  }

  if (generating && !data) return <GeneratingScreen />

  if (error && NEEDS_GOAL_PATTERN.test(error)) {
    return (
      <main className="min-h-screen flex items-center justify-center px-6">
        <div className="text-center max-w-md">
          <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-slate-400 mb-3">
            职业生涯发展报告
          </p>
          <p className="text-[32px] md:text-[40px] font-extrabold text-slate-900 leading-[1.1] tracking-[-0.02em]">
            先给自己定个方向。
          </p>
          <p className="mt-4 text-[13px] text-slate-500 max-w-[38ch] mx-auto leading-relaxed">
            报告围绕你选的方向写：你离它多远、差什么、下一步做哪件事。没有方向，报告就没抓手。
          </p>
          <div className="mt-6 flex items-center justify-center gap-5">
            <button
              onClick={() => navigate('/graph')}
              className="inline-flex items-center gap-1 text-[13px] font-semibold text-slate-900 border-b-2 border-slate-900 pb-0.5 hover:text-blue-700 hover:border-blue-700 transition-colors cursor-pointer"
            >
              去岗位图谱选方向 →
            </button>
            <button
              onClick={() => navigate('/')}
              className="text-[13px] text-slate-400 hover:text-slate-700 transition-colors cursor-pointer"
            >
              返回首页
            </button>
          </div>
        </div>
      </main>
    )
  }

  if (error && !data) {
    return (
      <main className="min-h-screen flex items-center justify-center px-6">
        <div className="text-center max-w-md">
          <p className="text-[22px] font-bold text-slate-900">生成报告时出了点问题</p>
          <p className="mt-2 text-[13px] text-slate-500 leading-relaxed">{error}</p>
          <button
            onClick={loadInitial}
            className="mt-6 inline-flex items-center gap-1 text-[13px] font-semibold text-slate-900 border-b-2 border-slate-900 pb-0.5 hover:text-blue-700 hover:border-blue-700 transition-colors cursor-pointer"
          >
            再试一次 →
          </button>
        </div>
      </main>
    )
  }

  if (!data) {
    return (
      <main className="min-h-screen flex items-center justify-center px-6">
        <div className="text-center max-w-md">
          <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-slate-400 mb-3">
            职业生涯发展报告
          </p>
          <p className="text-[32px] md:text-[40px] font-extrabold text-slate-900 leading-[1.1] tracking-[-0.02em]">
            这一份还没生成过。
          </p>
          <p className="mt-3 text-[13px] text-slate-500 max-w-[36ch] mx-auto leading-relaxed">
            基于你的档案和成长记录，写一份关于你是谁、能去哪、差什么的报告。写一次大约需要几分钟。
          </p>
          <button
            onClick={generate}
            disabled={generating}
            className="mt-6 inline-flex items-center gap-1 text-[13px] font-semibold text-slate-900 border-b-2 border-slate-900 pb-0.5 hover:text-blue-700 hover:border-blue-700 transition-colors cursor-pointer disabled:opacity-50"
          >
            开始写 →
          </button>
        </div>
        <ToastContainer toast={toast} onClose={() => setToast(null)} />
      </main>
    )
  }

  return (
    <main className="min-h-screen @container">
      <div className="mx-auto px-4 md:px-8 py-5 pb-24 w-full max-w-[780px] @[1080px]:max-w-[1000px] @[1080px]:grid @[1080px]:grid-cols-[minmax(0,780px)_160px] @[1080px]:gap-10 @[1080px]:justify-center">
        <div className="min-w-0">
          <ChapterI
            data={data}
            onSave={(t) => saveChapter('narrative', t)}
            saving={saving}
          />
          <ChapterII
            data={data}
            onSave={(t) => saveChapter('chapter-2', t)}
            saving={saving}
          />
          <ChapterIII
            data={data}
            onSave={(t) => saveChapter('chapter-3', t)}
            saving={saving}
          />
          <ChapterIV
            data={data}
            onSave={(t) => saveChapter('chapter-4', t)}
            saving={saving}
          />
          <Epilogue
            generatedAt={data.generated_at}
            onRegenerate={generate}
            regenerating={generating}
            onExport={handleExport}
            onPolish={async () => {
              if (currentId == null) return
              setSaving(true)
              try {
                const result = await polishReport(currentId)
                setData((prev) => prev ? { ...prev, narrative: result.polished?.narrative || prev.narrative } : prev)
                setToast({ message: '润色完成', type: 'success', durationMs: 2000 })
              } catch (e) {
                setToast({ message: '润色失败', type: 'error', durationMs: 3000 })
              } finally {
                setSaving(false)
              }
            }}
            polishing={saving}
          />
        </div>
        <aside className="hidden @[1080px]:block pt-32 print:hidden">
          <TableOfContents
            items={[
              { id: 'chapter-1', numeral: 'I', label: '你是谁' },
              { id: 'chapter-2', numeral: 'II', label: '你能去哪' },
              { id: 'chapter-3', numeral: 'III', label: '差距' },
              { id: 'chapter-4', numeral: 'IV', label: '下一步' },
            ]}
          />
        </aside>
      </div>
      <ToastContainer toast={toast} onClose={() => setToast(null)} />
    </main>
  )
}
