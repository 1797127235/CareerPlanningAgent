import type { ReportV2Data } from '@/api/report'
import { ChapterOpener, Chapter } from './index'
import { splitParagraphs } from './reportUtils'

export function ChapterIII({ data }: { data: ReportV2Data }) {
  // 差距靠叙事表达，不用分数不用技能清单 —— 量化差距会变成 LinkedIn 式评分卡。
  // 材料：differentiation_advice (AI 写的定性判断) + diagnosis 的 needs_improvement 项。
  const advice = (data.differentiation_advice ?? '').trim()
  const adviceParas = splitParagraphs(advice, 2, 3)

  const needsImp = (data.diagnosis ?? [])
    .filter((d) => d.status === 'needs_improvement')
    .slice(0, 3)

  const hasContent = adviceParas.length > 0 || needsImp.length > 0

  return (
    <div id="chapter-3">
      <ChapterOpener numeral="III" label="差距" headline="你还差的，说清楚。" />
      <Chapter>
        {!hasContent && (
          <p className="text-[17px] leading-[1.8] text-slate-500">
            关于差距的分析还没写出来。点上方的「再生成」可以重跑一次。
          </p>
        )}

        {adviceParas.map((p, i) => (
          <p key={i} className={i === 0 ? '' : 'mt-5'}>
            {p}
          </p>
        ))}

        {needsImp.length > 0 && (
          <div className="mt-10">
            <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500 mb-4">
              几件具体要改的事
            </p>
            <div className="pl-5 border-l-2 border-slate-300 space-y-5">
              {needsImp.map((d, i) => (
                <div key={(d.source_id ?? 0) + '-' + i}>
                  <p className="text-[15px] text-slate-800 leading-relaxed">
                    {d.highlight && <span className="font-semibold">{d.highlight}</span>}
                    {d.suggestion && (
                      <span className="text-slate-600">
                        {d.highlight ? ' —— ' : ''}
                        {d.suggestion}
                      </span>
                    )}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </Chapter>
    </div>
  )
}
