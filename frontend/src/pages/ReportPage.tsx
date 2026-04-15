/**
 * ReportPage — v2 narrative structure rendered with v1 editorial language.
 *
 * Load strategy:
 *   - On mount, fast-path via fetchReportList + fetchReportDetail to show any
 *     existing report in milliseconds.
 *   - The slow POST /report/generate is only called when the user explicitly
 *     asks for it (empty-state "开始写" or Prologue/Epilogue "再生成").
 *   - While a fresh generation is in flight without prior data to show, render
 *     the GeneratingScreen with rotating copy (30-60s waits don't feel frozen).
 *   - During regen *with* existing data, keep rendering the old report and let
 *     the Prologue/Epilogue buttons show "正在重新生成…" via the regenerating prop.
 */
import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  generateReportV2,
  fetchReportList,
  fetchReportDetail,
  type ReportV2Data,
} from '@/api/report'
import {
  Prologue,
  ChapterI,
  ChapterII,
  ChapterIII,
  ChapterIV,
  Epilogue,
  TableOfContents,
} from '@/components/report'

function LoadingDots() {
  const [n, setN] = useState(0)
  useEffect(() => {
    const id = window.setInterval(() => setN((v) => (v + 1) % 4), 420)
    return () => window.clearInterval(id)
  }, [])
  return <span className="inline-block w-6 text-left tabular-nums">{'.'.repeat(n)}</span>
}

// Precondition-not-met messages from backend that should route to wayfinding.
const NEEDS_GOAL_PATTERN = /设定.*(目标|方向)|岗位图谱|先(选|选择|选定).*(目标|方向)/

// Progressive copy shown during the long POST /generate call. Each entry is
// deliberately generic about AI ordering; backend isn't actually chunking work
// this way, but the cadence matches human expectation for "it's working".
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
        <p className="text-[28px] md:text-[32px] font-bold text-slate-900 tracking-tight leading-[1.2] transition-opacity duration-300">
          {GENERATING_MESSAGES[idx]}
          <LoadingDots />
        </p>
        <p className="mt-4 text-[13px] text-slate-500 max-w-[36ch] mx-auto leading-relaxed">
          AI 在写这一份，大概 30 到 60 秒。
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
  void isMock // reserved for future mock wiring

  const [data, setData] = useState<ReportV2Data | null>(null)
  const [loading, setLoading] = useState(true)     // fast initial fetch
  const [generating, setGenerating] = useState(false) // slow POST /generate
  const [error, setError] = useState<string | null>(null)

  // Fast initial load: show an existing report without triggering /generate.
  const loadInitial = async () => {
    setLoading(true)
    setError(null)
    try {
      const list = await fetchReportList()
      if (list.length === 0) {
        // No report yet → fall through to empty state.
        return
      }
      const latest = list[0] // backend returns newest first
      const detail = await fetchReportDetail(latest.id)
      const reportData = detail.data as unknown as ReportV2Data
      if (reportData && reportData.target) {
        setData(reportData)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '请求失败')
    } finally {
      setLoading(false)
    }
  }

  // Slow path: force a fresh generation. Keeps prior data visible during regen.
  const generate = async () => {
    setGenerating(true)
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
      setGenerating(false)
    }
  }

  useEffect(() => {
    loadInitial()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Fast initial fetch — keep copy minimal; it should blink by in <1s.
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

  // Slow generation with no existing data behind it — rotate through progress copy.
  if (generating && !data) {
    return <GeneratingScreen />
  }

  // Precondition: needs goal. Guide, don't scold.
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

  // Unknown error, no prior data — full error screen.
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

  // No report yet — invite the first generation.
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
            基于你的档案和成长记录，写一份关于你是谁、能去哪、差什么的报告。写一次大约 30 到 60 秒。
          </p>
          <button
            onClick={generate}
            disabled={generating}
            className="mt-6 inline-flex items-center gap-1 text-[13px] font-semibold text-slate-900 border-b-2 border-slate-900 pb-0.5 hover:text-blue-700 hover:border-blue-700 transition-colors cursor-pointer disabled:opacity-50"
          >
            开始写 →
          </button>
        </div>
      </main>
    )
  }

  return (
    // @container makes <main> a size query container. TOC activates only when
    // the main area inline-size is ≥1080px — which naturally hides it when the
    // right chat panel is open on narrower viewports (no collision).
    <main className="min-h-screen @container">
      <div className="mx-auto px-4 md:px-8 py-5 pb-24 w-full max-w-[780px] @[1080px]:max-w-[1000px] @[1080px]:grid @[1080px]:grid-cols-[minmax(0,780px)_160px] @[1080px]:gap-10 @[1080px]:justify-center">
        <div className="min-w-0">
          <Prologue
            target={data.target}
            matchScore={data.match_score}
            generatedAt={data.generated_at}
            onRegenerate={generate}
            regenerating={generating}
          />
          <ChapterI data={data} />
          <ChapterII data={data} />
          <ChapterIII data={data} />
          <ChapterIV data={data} />
          <Epilogue
            generatedAt={data.generated_at}
            onRegenerate={generate}
            regenerating={generating}
          />
        </div>
        <aside className="hidden @[1080px]:block pt-32">
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
    </main>
  )
}
