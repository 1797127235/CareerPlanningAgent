import type { ReportV2Data } from '@/api/report'
import { ChapterOpener, Chapter } from './index'

export function ChapterIII({ data }: { data: ReportV2Data }) {
  const fd = data.four_dim
  const hasFD =
    fd?.foundation != null || fd?.skills != null || fd?.qualities != null || fd?.potential != null
  const missing = (data.skill_gap?.top_missing ?? []).slice(0, 6)
  const needsImp = (data.diagnosis ?? []).filter((d) => d.status === 'needs_improvement').slice(0, 3)

  const fdRows: [string, number | null][] = fd
    ? [
        ['基础', fd.foundation],
        ['技能', fd.skills],
        ['素质', fd.qualities],
        ['潜力', fd.potential],
      ]
    : []

  return (
    <div id="chapter-3">
      <ChapterOpener numeral="III" label="差距" headline="你还差的，说清楚。" />
      <Chapter>
        {hasFD && (
          <div className="mt-2 mb-12">
            <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500 mb-4">
              四维评估
            </p>
            <div className="grid grid-cols-4 gap-4">
              {fdRows.map(([label, v]) => (
                <div key={label}>
                  <span className="block text-[28px] font-extrabold tabular-nums text-slate-900 leading-none">
                    {v != null ? v : '—'}
                  </span>
                  <div className="mt-3 h-[2px] bg-slate-200 overflow-hidden">
                    {v != null && (
                      <div
                        className="h-full bg-slate-900"
                        style={{ width: `${Math.min(100, Math.max(0, v))}%` }}
                      />
                    )}
                  </div>
                  <p className="mt-2 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
                    {label}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {missing.length > 0 && (
          <div className="mt-10">
            <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500 mb-3">
              还差的关键技能
            </p>
            <ul className="divide-y divide-slate-200 border-y border-slate-200">
              {missing.map((s, i) => (
                <li key={s.name + i} className="flex items-baseline justify-between py-3 gap-4">
                  <span className="text-[15px] font-semibold text-slate-900">{s.name}</span>
                  <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-400 tabular-nums">
                    {Math.round(s.freq * 100)}% · {s.tier}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {needsImp.length > 0 && (
          <div className="mt-10">
            <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500 mb-3">
              可以改进的点
            </p>
            <div className="pl-5 border-l-2 border-slate-300 space-y-4">
              {needsImp.map((d, i) => (
                <div key={(d.source_id ?? 0) + '-' + i}>
                  <p className="text-[15px] text-slate-800 leading-relaxed">
                    {d.highlight && <span className="font-semibold">{d.highlight} </span>}
                    {d.suggestion && <span className="text-slate-600">— {d.suggestion}</span>}
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
