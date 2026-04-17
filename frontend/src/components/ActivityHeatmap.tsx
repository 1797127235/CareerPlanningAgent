import { useState, useMemo, useRef, useEffect } from 'react'

interface HeatmapDay {
  date: string
  count: number
  activities: string[]
}

interface Props {
  days: HeatmapDay[]
  weeks?: number
}

const LEVEL_COLORS = [
  'bg-slate-100/60',  // 0 — 近透明，不抢眼
  'bg-blue-300',      // 1-2
  'bg-blue-500',      // 3-5
  'bg-blue-700',      // 6+
]

function getLevel(count: number) {
  if (count === 0) return 0
  if (count <= 2) return 1
  if (count <= 5) return 2
  return 3
}

function formatTooltipDate(dateStr: string) {
  const d = new Date(dateStr + 'T00:00:00')
  const weekdays = ['日', '一', '二', '三', '四', '五', '六']
  return `${d.getMonth() + 1}月${d.getDate()}日 周${weekdays[d.getDay()]}`
}

const LABEL_W = 24 // weekday label width
const GAP = 4

export function ActivityHeatmap({ days, weeks = 16 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [cellSize, setCellSize] = useState(0)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const [tooltip, setTooltip] = useState<{
    date: string; count: number; activities: string[]
  } | null>(null)
  const [tooltipPos, setTooltipPos] = useState<{ left: number; top: number }>({ left: 0, top: 0 })

  // Build full grid: weeks × 7 days
  const grid = useMemo(() => {
    const dayMap = new Map(days.map(d => [d.date, d]))
    const today = new Date()
    const startDate = new Date(today)
    startDate.setDate(startDate.getDate() - (weeks * 7) + 1)
    const dayOfWeek = startDate.getDay()
    const mondayOffset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek
    startDate.setDate(startDate.getDate() + mondayOffset)

    const columns: Array<Array<{ date: string; count: number; activities: string[] }>> = []
    const current = new Date(startDate)

    while (current <= today) {
      const week: typeof columns[0] = []
      for (let d = 0; d < 7; d++) {
        const dateStr = current.toISOString().slice(0, 10)
        const data = dayMap.get(dateStr)
        week.push({
          date: dateStr,
          count: data?.count ?? 0,
          activities: data?.activities ?? [],
        })
        current.setDate(current.getDate() + 1)
      }
      columns.push(week)
    }
    return columns
  }, [days, weeks])

  // Auto-size cells to fill width
  useEffect(() => {
    function calc() {
      if (!containerRef.current) return
      const w = containerRef.current.offsetWidth - LABEL_W
      const cols = grid.length || 16
      const size = Math.floor((w - GAP * (cols - 1)) / cols)
      setCellSize(Math.max(size, 10))
    }
    calc()
    window.addEventListener('resize', calc)
    return () => window.removeEventListener('resize', calc)
  }, [grid.length])

  // Month labels
  const monthLabels = useMemo(() => {
    const labels: Array<{ text: string; col: number }> = []
    let lastMonth = -1
    grid.forEach((week, i) => {
      const m = new Date(week[0].date + 'T00:00:00').getMonth()
      if (m !== lastMonth) {
        labels.push({ text: `${m + 1}月`, col: i })
        lastMonth = m
      }
    })
    return labels
  }, [grid])

  if (!cellSize) {
    return <div ref={containerRef} className="h-[120px]" />
  }

  const colStep = cellSize + GAP

  return (
    <div ref={containerRef} className="relative select-none">
      {/* Month labels row */}
      <div className="relative h-[18px] mb-1" style={{ marginLeft: LABEL_W }}>
        {monthLabels.map((m, i) => (
          <span
            key={i}
            className="absolute text-[12px] text-slate-500 font-medium"
            style={{ left: m.col * colStep }}
          >
            {m.text}
          </span>
        ))}
      </div>

      {/* Grid area */}
      <div className="flex">
        {/* Weekday labels */}
        <div className="flex flex-col shrink-0" style={{ width: LABEL_W, gap: GAP }}>
          {[0, 1, 2, 3, 4, 5, 6].map(d => (
            <div key={d} className="flex items-center justify-end pr-1.5" style={{ height: cellSize }}>
              <span className="text-[11px] text-slate-400 leading-none">
                {d === 0 ? '一' : d === 2 ? '三' : d === 4 ? '五' : d === 6 ? '日' : ''}
              </span>
            </div>
          ))}
        </div>

        {/* Cells */}
        <div className="flex flex-1" style={{ gap: GAP }}>
          {grid.map((week, wi) => (
            <div key={wi} className="flex flex-col" style={{ gap: GAP }}>
              {week.map(day => {
                const level = getLevel(day.count)
                const isFuture = new Date(day.date + 'T00:00:00') > new Date()
                return (
                  <div
                    key={day.date}
                    className={`rounded-[3px] cursor-default ${isFuture ? 'bg-transparent' : LEVEL_COLORS[level]} hover:ring-2 hover:ring-blue-300/50 hover:scale-110 transition-all duration-150`}
                    style={{ width: cellSize, height: cellSize }}
                    onMouseEnter={(e) => {
                      if (isFuture) return
                      const rect = e.currentTarget.getBoundingClientRect()
                      const containerRect = containerRef.current?.getBoundingClientRect()
                      setTooltip({ date: day.date, count: day.count, activities: day.activities })
                      setTooltipPos({
                        left: rect.left + rect.width / 2 - (containerRect?.left ?? 0),
                        top: rect.top - (containerRect?.top ?? 0) - 10,
                      })
                    }}
                    onMouseLeave={() => setTooltip(null)}
                  />
                )
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-1.5 mt-3" style={{ marginLeft: LABEL_W }}>
        <span className="text-[11px] text-slate-400">少</span>
        {LEVEL_COLORS.map((cls, i) => (
          <div key={i} className={`w-[14px] h-[14px] rounded-[3px] ${cls}`} />
        ))}
        <span className="text-[11px] text-slate-400">多</span>
      </div>

      {/* Tooltip — GitHub style */}
      {tooltip && (
        <div
          ref={tooltipRef}
          className="absolute z-[100] pointer-events-none"
          style={{
            left: tooltipPos.left,
            top: tooltipPos.top,
            transform: 'translate(-50%, -100%)',
          }}
        >
          <div className="bg-slate-800 text-white text-[12px] rounded-md px-3 py-1.5 shadow-lg whitespace-nowrap">
            {tooltip.count > 0
              ? `${tooltip.count} 项活动 于 ${formatTooltipDate(tooltip.date)}`
              : `${formatTooltipDate(tooltip.date)} 无活动`
            }
          </div>
          <div className="flex justify-center -mt-[1px]">
            <div className="w-2 h-2 bg-slate-800 rotate-45" />
          </div>
        </div>
      )}
    </div>
  )
}
