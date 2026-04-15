import type { ReportV2Data } from '@/api/report'
import { ChapterOpener, Chapter, DropCap } from './index'

export function ChapterII({ data }: { data: ReportV2Data }) {
  const obs = data.career_alignment?.observations ?? ''
  const alignments = (data.career_alignment?.alignments ?? []).slice(0, 3)

  const marketBits: string[] = []
  if (data.market?.salary_p50) marketBits.push(`薪资 p50 ¥${data.market.salary_p50.toLocaleString()}`)
  if (data.market?.timing_label) marketBits.push(data.market.timing_label)
  if (data.market?.demand_change_pct != null) {
    const sign = data.market.demand_change_pct >= 0 ? '+' : ''
    marketBits.push(`需求 ${sign}${data.market.demand_change_pct}%`)
  }

  return (
    <div id="chapter-2">
      <ChapterOpener
        numeral="II"
        label="你能去哪"
        headline={`在${data.target.label}方向上，你还能走多远。`}
      />
      <Chapter>
        {obs ? (
          <DropCap>{obs}</DropCap>
        ) : (
          <p className="text-[17px] leading-[1.8] text-slate-700">
            关于这个方向的整体判断暂时还没有生成。点上方的「再生成」可以重跑一次。
          </p>
        )}

        {alignments.length > 0 && (
          <div className="mt-10">
            <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500 mb-4">
              与你的吻合度
            </p>
            <div className="space-y-5">
              {alignments.map((a) => (
                <div key={a.node_id} className="flex items-baseline gap-5">
                  <span className="text-[26px] font-extrabold tabular-nums text-slate-900 w-14 shrink-0 leading-none">
                    {a.score}
                  </span>
                  <div className="flex-1">
                    <p className="text-[15px] font-semibold text-slate-900">{a.label}</p>
                    {a.evidence && (
                      <p className="text-[13px] text-slate-500 mt-1 leading-relaxed">{a.evidence}</p>
                    )}
                    {a.gap && (
                      <p className="text-[12px] text-slate-400 mt-1">差距：{a.gap}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {marketBits.length > 0 && (
          <div className="mt-10 pt-5 border-t border-slate-200">
            <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500 mb-2">
              市场信号
            </p>
            <p className="text-[14px] text-slate-700 tabular-nums">{marketBits.join(' · ')}</p>
          </div>
        )}
      </Chapter>
    </div>
  )
}
