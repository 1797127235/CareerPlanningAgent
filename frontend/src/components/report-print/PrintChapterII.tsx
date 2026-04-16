import { useEffect, useRef, useState } from 'react'
import type { ReportV2Data } from '@/api/report'
import { flowIntoColumns, type PlacedLine } from './utils/flowColumns'
import { fitHeadline } from './utils/fitHeadline'

interface PrintChapterIIProps {
  data: ReportV2Data
  onLayoutDone?: () => void
}

const BODY_FONT = '14px "Source Han Serif SC", serif'
const BODY_LINE_HEIGHT = 24
const PARA_GAP = 10

export function PrintChapterII({ data, onLayoutDone }: PrintChapterIIProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [paraLines, setParaLines] = useState<PlacedLine[][]>([])
  const [totalHeight, setTotalHeight] = useState(0)
  const [headlineSize, setHeadlineSize] = useState(28)

  const override = data.chapter_narratives?.['chapter-2']
  const baseObs = data.career_alignment?.observations ?? ''
  const proseText = (override ?? baseObs).trim()
  const paragraphs = proseText.split(/\n{2,}/).map((p) => p.trim()).filter((p) => p.length > 0)

  const alignments = (data.career_alignment?.alignments ?? []).slice(0, 3)

  const marketBits: string[] = []
  if (data.market?.salary_p50)
    marketBits.push(`薪资 p50 ¥${data.market.salary_p50.toLocaleString()}`)
  if (data.market?.timing_label) marketBits.push(data.market.timing_label)
  if (data.market?.demand_change_pct != null) {
    const sign = data.market.demand_change_pct >= 0 ? '+' : ''
    marketBits.push(`需求 ${sign}${data.market.demand_change_pct}%`)
  }

  const pullquoteText =
    data.market_narrative || marketBits.join(' · ') || '岗位处于持续需求期，是中长期的稳妥选择。'

  useEffect(() => {
    if (!containerRef.current) return
    const w = containerRef.current.offsetWidth
    const headline = `在${data.target.label}方向上，你还能走多远。`
    setHeadlineSize(fitHeadline(headline, 'Source Han Serif SC', 700, w, 2, 24, 42))

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
  }, [proseText, data.target.label, onLayoutDone])

  return (
    <section className="print-chapter">
      <div ref={containerRef} style={{ maxWidth: 560, margin: '0 auto' }}>
        <div className="mb-6">
          <span className="text-[10px] font-bold uppercase tracking-widest text-blue-600">
            II · 你能去哪
          </span>
          <h2
            className="font-bold mt-2 text-slate-900"
            style={{
              fontSize: headlineSize,
              fontFamily: '"Source Han Serif SC", serif',
              lineHeight: 1.15,
            }}
          >
            在{data.target.label}方向上，你还能走多远。
          </h2>
        </div>

        {paragraphs.length > 0 && (
          <div className="relative" style={{ height: totalHeight }}>
            {paraLines.flat().map((ln, i) => (
              <div
                key={i}
                style={{
                  position: 'absolute',
                  left: ln.x,
                  top: ln.y,
                  width: ln.width,
                  fontSize: 14,
                  lineHeight: `${BODY_LINE_HEIGHT}px`,
                  fontFamily: '"Source Han Serif SC", serif',
                  color: '#0f172a',
                }}
              >
                {ln.text}
              </div>
            ))}
          </div>
        )}

        <blockquote className="mt-8 py-4 text-[15px] italic font-bold text-slate-900 text-center leading-relaxed">
          {pullquoteText}
        </blockquote>

        {alignments.length > 0 && (
          <div className="mt-8">
            <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500 mb-4">
              与你的吻合度
            </p>
            <div className="space-y-4">
              {alignments.map((a) => (
                <div key={a.node_id} className="print-avoid-break">
                  <div className="flex items-baseline gap-3">
                    <p className="text-[24px] font-extrabold tabular-nums text-slate-900 leading-none">
                      {a.score}
                    </p>
                    <p className="text-[14px] font-semibold text-slate-900">{a.label}</p>
                  </div>
                  {a.evidence && (
                    <p className="text-[12px] text-slate-500 mt-2 leading-relaxed">{a.evidence}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
