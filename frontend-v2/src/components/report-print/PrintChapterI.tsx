import { useEffect, useRef, useState } from 'react'
import type { ReportV2Data } from '@/api/report'
import { flowIntoColumns, type PlacedLine } from './utils/flowColumns'
import { fitHeadline } from './utils/fitHeadline'

interface PrintChapterIProps {
  data: ReportV2Data
  onLayoutDone?: () => void
}

const BODY_FONT = '14px "Source Han Serif SC", serif'
const BODY_LINE_HEIGHT = 30
const PARA_GAP = 16

export function PrintChapterI({ data, onLayoutDone }: PrintChapterIProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [paraLines, setParaLines] = useState<PlacedLine[][]>([])
  const [totalHeight, setTotalHeight] = useState(0)
  const [headlineSize, setHeadlineSize] = useState(32)

  const narrative = data.narrative || ''
  const paragraphs = narrative
    .split(/\n{2,}/)
    .map((p) => p.trim().replace(/\s+/g, ' '))  // 把段落内的 \n / tab / 连续空格都折叠成单个空格
    .filter((p) => p.length > 0)

  useEffect(() => {
    if (!containerRef.current) return
    const w = containerRef.current.offsetWidth
    setHeadlineSize(fitHeadline('先把你自己看清楚。', 'Source Han Serif SC', 700, w, 1, 24, 48))

    const allParas: PlacedLine[][] = []
    let yCursor = 0
    for (const para of paragraphs) {
      const lines = flowIntoColumns(
        para,
        BODY_FONT,
        BODY_LINE_HEIGHT,
        [{ x: 0, y: 0, width: w, height: 9999 }],
        [],
      )
      const shifted = lines.map((l) => ({ ...l, y: l.y + yCursor }))
      allParas.push(shifted)
      if (lines.length > 0) {
        yCursor += lines[lines.length - 1].y + BODY_LINE_HEIGHT + PARA_GAP
      }
    }
    setParaLines(allParas)
    setTotalHeight(Math.max(0, yCursor - PARA_GAP))
    onLayoutDone?.()
  }, [narrative, onLayoutDone])

  const diag = data.diagnosis || []
  const quote =
    diag.find((d) => d.status === 'pass' && d.current_text?.length > 10) ??
    diag.find((d) => d.current_text?.length > 10)
  const quoteText = quote
    ? quote.current_text.length > 80
      ? quote.current_text.slice(0, 80) + '…'
      : quote.current_text
    : null
  const quoteSource = quote?.source ?? '你的成长轨迹'

  return (
    <section className="print-chapter">
      <div ref={containerRef} style={{ maxWidth: 560, margin: '0 auto' }}>
        <div className="mb-6">
          <span className="text-[10px] font-bold uppercase tracking-widest text-blue-600">
            I · 你是谁
          </span>
          <h2
            className="font-bold mt-2 text-slate-900"
            style={{
              fontSize: headlineSize,
              fontFamily: '"Source Han Serif SC", serif',
              lineHeight: 1.1,
            }}
          >
            先把你自己看清楚。
          </h2>
        </div>

        <div className="relative" style={{ height: totalHeight }}>
          {paraLines.flat().map((ln, i) => (
            <div
              key={i}
              style={{
                position: 'absolute',
                left: ln.x,
                top: ln.y,
                fontSize: 14,
                lineHeight: `${BODY_LINE_HEIGHT}px`,
                fontFamily: '"Source Han Serif SC", serif',
                color: '#0f172a',
                whiteSpace: 'pre',  // 禁止浏览器二次 wrap + 保留 pretext 输出里的空格（和官方 editorial-engine demo 对齐）
              }}
            >
              {ln.text}
            </div>
          ))}
        </div>

        <blockquote className="mt-8 pl-4 border-l border-slate-300 text-[13px] italic text-slate-600 leading-relaxed">
          {quoteText || '先把自己正在做的记下来 —— 回看时你会看到自己走了多远。'}
          <cite className="block mt-2 not-italic text-[11px] text-slate-400">
            —— 摘自你的「{quoteSource}」
          </cite>
        </blockquote>
      </div>
    </section>
  )
}
