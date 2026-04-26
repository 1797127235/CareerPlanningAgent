import { useEffect, useRef, useState } from 'react'
import type { ReportV2Data } from '@/api/report'
import { fitHeadline } from './utils/fitHeadline'
import { sanitizeFieldLeaks } from './utils/sanitizeFieldLeaks'

interface PrintChapterIIIProps {
  data: ReportV2Data
  onLayoutDone?: () => void
}

export function PrintChapterIII({ data, onLayoutDone }: PrintChapterIIIProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [headlineSize, setHeadlineSize] = useState(28)

  const override = data.chapter_narratives?.['chapter-3']
  const baseAdvice = (data.differentiation_advice ?? '').trim()
  const proseText = (override ?? baseAdvice).trim()
  const paragraphs = proseText
    .split(/\n{2,}/)
    .filter((p) => p.trim().length > 0)
    .map((p) => sanitizeFieldLeaks(p))

  const needsImp = (data.diagnosis ?? [])
    .filter((d) => d.status === 'needs_improvement')
    .slice(0, 3)

  useEffect(() => {
    if (!containerRef.current) return
    const w = containerRef.current.offsetWidth
    setHeadlineSize(fitHeadline('你还差的，说清楚。', 'Source Han Serif SC', 700, w, 1, 24, 42))
    onLayoutDone?.()
  }, [onLayoutDone])

  return (
    <section className="print-chapter">
      <div ref={containerRef} style={{ maxWidth: 560, margin: '0 auto' }}>
      <div className="mb-6">
        <span className="text-[10px] font-bold uppercase tracking-widest text-blue-600">
          III · 差距
        </span>
        <h2
          className="font-bold mt-2 text-slate-900"
          style={{
            fontSize: headlineSize,
            fontFamily: '"Source Han Serif SC", serif',
            lineHeight: 1.1,
          }}
        >
          你还差的，说清楚。
        </h2>
      </div>

      {paragraphs.length > 0 && (
        <div className="mb-8 text-[14px] leading-[22px] font-['Source_Han_Serif_SC',serif] whitespace-pre-wrap">
          {paragraphs.join('\n\n')}
        </div>
      )}

      {needsImp.length > 0 && (
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500 mb-4">
            几件具体要改的事
          </p>
          <div className="space-y-4">
            {needsImp.map((d, i) => (
              <div key={(d.source_id ?? 0) + '-' + i} className="print-avoid-break">
                <p className="text-[13px] text-slate-800 leading-relaxed">
                  {d.highlight && <span className="font-semibold">{sanitizeFieldLeaks(d.highlight)}</span>}
                  {d.suggestion && (
                    <span className="text-slate-600">
                      {d.highlight ? ' —— ' : ''}
                      {sanitizeFieldLeaks(d.suggestion)}
                    </span>
                  )}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
      </div>
    </section>
  )
}
