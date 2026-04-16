import { useEffect, useRef, useState } from 'react'
import type { ReportV2Data } from '@/api/report'
import { fitHeadline } from './utils/fitHeadline'

interface PrintChapterIVProps {
  data: ReportV2Data
  onLayoutDone?: () => void
}

const TYPE_LABEL: Record<string, string> = {
  skill: '技能',
  project: '项目',
  job_prep: '求职',
}

const STAGE_NUMERAL = ['一', '二', '三']

export function PrintChapterIV({ data, onLayoutDone }: PrintChapterIVProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [headlineSize, setHeadlineSize] = useState(28)

  const rawStages = data.action_plan?.stages ?? []
  const stages = rawStages.filter((s) => (s.items || []).length > 0)

  useEffect(() => {
    if (!containerRef.current) return
    const w = containerRef.current.offsetWidth
    const headline =
      stages.length >= 2
        ? '从阶段一开始，一步步往下走。'
        : stages.length === 1
          ? '先把这几件具体的事做掉。'
          : '暂时还没有足够证据生成行动计划。'
    setHeadlineSize(fitHeadline(headline, 'Source Han Serif SC', 700, w, 2, 22, 36))
    onLayoutDone?.()
  }, [stages.length, onLayoutDone])

  const headline =
    stages.length >= 2
      ? '从阶段一开始，一步步往下走。'
      : stages.length === 1
        ? '先把这几件具体的事做掉。'
        : '暂时还没有足够证据生成行动计划。'

  return (
    <section className="print-chapter">
      <div ref={containerRef} style={{ maxWidth: 560, margin: '0 auto' }}>
      <div className="mb-6">
        <span className="text-[10px] font-bold uppercase tracking-widest text-blue-600">
          IV · 下一步
        </span>
        <h2
          className="font-bold mt-2 text-slate-900"
          style={{
            fontSize: headlineSize,
            fontFamily: '"Source Han Serif SC", serif',
            lineHeight: 1.15,
          }}
        >
          {headline}
        </h2>
      </div>

      {stages.length === 0 ? (
        <p className="text-[14px] text-slate-500 leading-relaxed max-w-[60ch]">
          你的画像和成长档案里还没有足够的具体信号支撑行动建议——去记一条最近的学习笔记、项目进展或面试反思，再回来重新生成。
        </p>
      ) : (
        <div className="space-y-8">
          {stages.map((stage) => (
            <div key={stage.stage}>
              <div className="flex items-baseline gap-3 mb-3">
                <span className="text-[10px] font-bold uppercase tracking-widest text-blue-600">
                  阶段{STAGE_NUMERAL[stage.stage - 1] || stage.stage}
                </span>
                <span className="text-[10px] text-slate-400 tabular-nums">{stage.duration}</span>
              </div>
              <h3
                className="font-bold text-slate-900"
                style={{
                  fontSize: 22,
                  fontFamily: '"Source Han Serif SC", serif',
                  lineHeight: 1.2,
                }}
              >
                {stage.label}
              </h3>
              {stage.milestone && (
                <p className="mt-1 text-[12px] text-slate-500 italic">里程碑：{stage.milestone}</p>
              )}

              <div className="mt-4 space-y-3">
                {(stage.items || []).map((item, idx) => {
                  const hasStructured = !!(item.observation || item.action)
                  return (
                    <div
                      key={item.id || `${stage.stage}-${idx}`}
                      className="print-avoid-break border border-slate-200 p-3 rounded-sm"
                    >
                      <p className="text-[9px] font-bold uppercase tracking-widest text-slate-500 mb-1">
                        {TYPE_LABEL[item.type] ?? '行动'}
                        {item.priority === 'high' && (
                          <span className="ml-1 text-blue-600">· 优先</span>
                        )}
                      </p>
                      {item.tag && (
                        <p className="text-[14px] font-bold text-slate-900 mb-2">{item.tag}</p>
                      )}
                      {hasStructured ? (
                        <>
                          {item.observation && (
                            <p className="text-[11px] text-slate-600 leading-relaxed mb-1">
                              {item.observation}
                            </p>
                          )}
                          {item.action && (
                            <p className="text-[11px] text-slate-900 leading-relaxed font-semibold">
                              {item.action}
                            </p>
                          )}
                        </>
                      ) : (
                        <p className="text-[11px] text-slate-700 leading-relaxed">{item.text}</p>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      )}
      </div>
    </section>
  )
}
