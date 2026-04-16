import { PaperCard } from '@/components/growth-log/PaperCard'

interface StageEvent {
  id: number
  trigger: string
  stage_completed?: number
  created_at: string
}

interface JourneyTimelineProps {
  targetLabel: string
  setAt: string
  stageEvents: StageEvent[]
}

function fmtDate(iso: string) {
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function triggerLabel(evt: StageEvent) {
  if (evt.trigger === 'initial') return '起步'
  if (evt.trigger === 'stage_complete') return `完成第 ${evt.stage_completed ?? 1} 阶段`
  if (evt.trigger === 'deep_reeval') return '重新校准'
  return evt.trigger
}

export function JourneyTimeline({ targetLabel, setAt, stageEvents }: JourneyTimelineProps) {
  const nodes: {
    id: string
    date: string
    label: string
    type: 'start' | 'stage' | 'now'
  }[] = [
    { id: 'start', date: fmtDate(setAt), label: `你选了 ${targetLabel}`, type: 'start' },
    ...stageEvents.map((e, idx) => ({
      id: `stage-${e.id}-${idx}`,
      date: fmtDate(e.created_at),
      label: triggerLabel(e),
      type: 'stage' as const,
    })),
    { id: 'now', date: '今天', label: '现在', type: 'now' as const },
  ]

  return (
    <PaperCard className="overflow-x-auto">
      <div className="min-w-[360px] px-2 py-4">
        <div className="flex items-center">
          {nodes.map((node, idx) => {
            const isLast = idx === nodes.length - 1
            return (
              <div key={node.id} className="flex items-center">
                {/* Node */}
                <div className="flex flex-col items-center gap-2 w-20 md:w-24 shrink-0">
                  {/* Dot */}
                  <div className="relative flex items-center justify-center w-4 h-4">
                    {node.type === 'start' && (
                      <svg width="16" height="16" viewBox="0 0 16 16">
                        <circle cx="8" cy="8" r="6" fill="var(--moss)" />
                      </svg>
                    )}
                    {node.type === 'stage' && (
                      <svg width="16" height="16" viewBox="0 0 16 16">
                        <circle cx="8" cy="8" r="5" fill="var(--ember)" />
                      </svg>
                    )}
                    {node.type === 'now' && (
                      <svg width="16" height="16" viewBox="0 0 16 16">
                        <circle cx="8" cy="8" r="5" fill="none" stroke="var(--chestnut)" strokeWidth="2" />
                      </svg>
                    )}
                  </div>
                  {/* Label */}
                  <div className="text-center">
                    <p className="text-[11px] font-medium text-[var(--ink-1)] leading-tight">
                      {node.label}
                    </p>
                    <p className="text-[10px] text-[var(--ink-3)] mt-0.5 tabular-nums">
                      {node.date}
                    </p>
                  </div>
                </div>
                {/* Connector line */}
                {!isLast && (
                  <div className="w-6 md:w-10 h-px bg-[var(--moss)] shrink-0 mx-1" />
                )}
              </div>
            )
          })}
        </div>
      </div>
    </PaperCard>
  )
}
