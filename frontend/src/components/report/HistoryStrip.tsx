import type { MouseEvent } from 'react'
import { Trash2 } from 'lucide-react'
import type { ReportListItem } from '@/api/report'

interface HistoryStripProps {
  items: ReportListItem[]
  currentId: number | null
  onSwitch: (id: number) => void
  onDelete: (item: ReportListItem) => void
  switchingTo?: number | null
}

function fmtDate(iso: string): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  return d.toISOString().slice(0, 10)
}

/**
 * Always-visible history strip between Prologue and Chapter I.
 * Top/bottom hairlines bracket the strip like a magazine "previous issues"
 * section. Horizontally scrollable when many reports exist. Current report
 * marked with filled slate-900 dot + bold tabular date.
 */
export function HistoryStrip({
  items,
  currentId,
  onSwitch,
  onDelete,
  switchingTo,
}: HistoryStripProps) {
  if (items.length === 0) return null

  return (
    <div className="my-10 border-t border-b border-slate-200 py-4">
      <div className="flex items-baseline gap-6">
        <p className="shrink-0 text-[10px] font-bold uppercase tracking-[0.22em] text-slate-400">
          历史 · {items.length} 份
        </p>
        <div className="flex-1 overflow-x-auto no-scrollbar">
          <ul className="flex items-center gap-5 whitespace-nowrap">
            {items.map((item) => {
              const isCurrent = item.id === currentId
              const isSwitching = switchingTo === item.id
              const date = fmtDate(item.created_at)
              return (
                <li
                  key={item.id}
                  className="group relative inline-flex items-baseline gap-2 shrink-0"
                >
                  <button
                    onClick={() => {
                      if (isCurrent || isSwitching) return
                      onSwitch(item.id)
                    }}
                    disabled={isCurrent || isSwitching}
                    className={[
                      'inline-flex items-baseline gap-2 cursor-pointer transition-colors',
                      isCurrent ? 'cursor-default' : 'hover:text-slate-900',
                    ].join(' ')}
                    aria-current={isCurrent ? 'true' : undefined}
                  >
                    <span
                      aria-hidden
                      className={[
                        'inline-block w-1.5 h-1.5 rounded-full self-center shrink-0 transition-colors',
                        isCurrent ? 'bg-slate-900' : 'bg-slate-300',
                      ].join(' ')}
                    />
                    <span
                      className={[
                        'text-[12px] tabular-nums transition-colors',
                        isCurrent ? 'font-semibold text-slate-900' : 'text-slate-500',
                      ].join(' ')}
                    >
                      {date}
                    </span>
                    <span
                      className={[
                        'text-[12px] font-semibold tabular-nums transition-colors',
                        isCurrent ? 'text-slate-900' : 'text-slate-400',
                      ].join(' ')}
                    >
                      {item.match_score ?? '—'}
                    </span>
                    {isSwitching && (
                      <span className="ml-1 text-[10px] font-medium uppercase tracking-[0.18em] text-slate-400">
                        加载中
                      </span>
                    )}
                  </button>
                  <button
                    onClick={(e: MouseEvent) => {
                      e.stopPropagation()
                      onDelete(item)
                    }}
                    className="opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity text-slate-300 hover:text-red-500 p-0.5 -mx-0.5 cursor-pointer"
                    aria-label={`删除 ${date} 的报告`}
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      </div>
    </div>
  )
}
