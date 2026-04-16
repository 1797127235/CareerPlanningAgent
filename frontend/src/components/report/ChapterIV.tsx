import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { ReportV2Data, PlanActionItem, PlanStage } from '@/api/report'
import { createEntry } from '@/api/growthEntries'
import type { GrowthEntry } from '@/components/growth-log-v2/mockData'
import { ChapterOpener, Chapter } from './index'

const TYPE_LABEL: Record<string, string> = {
  skill: '技能',
  project: '项目',
  job_prep: '求职',
}

const STAGE_NUMERAL = ['一', '二', '三']

function StageHeader({ stage }: { stage: PlanStage }) {
  return (
    <div className="mt-12 first:mt-0">
      <div className="flex items-baseline gap-3 mb-2">
        <span className="text-[11px] font-bold uppercase tracking-[0.22em] text-blue-600">
          阶段{STAGE_NUMERAL[stage.stage - 1] || stage.stage}
        </span>
        <span className="text-[11px] font-medium text-slate-400 tabular-nums">
          {stage.duration}
        </span>
      </div>
      <h2 className="text-[28px] font-bold text-slate-900 tracking-tight leading-[1.2]">
        {stage.label}
      </h2>
      {stage.milestone && (
        <p className="mt-2 text-[14px] text-slate-500 italic leading-relaxed">
          里程碑：{stage.milestone}
        </p>
      )}
    </div>
  )
}

function ActionArticle({ item }: { item: PlanActionItem }) {
  const queryClient = useQueryClient()
  const [recorded, setRecorded] = useState(false)

  // prefill 成长档案用 action 而不是 observation
  const prefillText = item.action || item.text
  const hasStructured = !!(item.observation || item.action)

  const recordMutation = useMutation({
    mutationFn: (data: Partial<GrowthEntry>) => createEntry(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['growth-entries'] })
      setRecorded(true)
    },
  })

  const handleRecord = () => {
    if (recorded || recordMutation.isPending) return
    const category: GrowthEntry['category'] =
      item.type === 'skill' ? 'learning' : item.type === 'project' ? 'project' : 'interview'
    recordMutation.mutate({
      content: prefillText,
      category,
      tags: item.tag ? [item.tag] : [],
      structured_data: null,
      is_plan: true,
      status: 'pending',
      due_type: 'daily',
      due_at: new Date(new Date().setHours(23, 59, 59, 999)).toISOString(),
      completed_at: null,
      ai_suggestions: null,
    })
  }

  return (
    <article className="mt-6 pt-5 border-t border-slate-200">
      <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500 mb-2">
        [{TYPE_LABEL[item.type] ?? '行动'}]
        {item.priority === 'high' && (
          <span className="ml-2 text-blue-600">· 优先</span>
        )}
      </p>
      {item.tag && (
        <h3 className="text-[18px] font-bold text-slate-900 tracking-tight mb-3">
          {item.tag}
        </h3>
      )}
      {hasStructured ? (
        <>
          {item.observation && (
            <div className="mb-3">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">观察</span>
              <p className="mt-1 text-[14px] text-slate-700 leading-relaxed max-w-[60ch]">
                {item.observation}
              </p>
            </div>
          )}
          {item.action && (
            <div className="mb-3">
              <span className="text-[11px] font-bold text-blue-600 uppercase tracking-wider">行动</span>
              <p className="mt-1 text-[14px] text-slate-900 leading-relaxed max-w-[60ch] font-medium">
                {item.action}
              </p>
            </div>
          )}
        </>
      ) : (
        <p className="text-[14px] text-slate-700 leading-relaxed max-w-[60ch]">
          {item.text}
        </p>
      )}
      <button
        onClick={handleRecord}
        disabled={recordMutation.isPending || recorded}
        className={[
          'mt-2 inline-flex items-center gap-1 text-[13px] font-semibold border-b-2 pb-0.5 transition-colors cursor-pointer',
          recorded
            ? 'text-green-600 border-green-600 cursor-default'
            : 'text-slate-900 border-slate-900 hover:text-blue-700 hover:border-blue-700',
        ].join(' ')}
      >
        {recordMutation.isPending ? '记录中…' : recorded ? '已记录 ✓' : '记到成长档案 →'}
      </button>
    </article>
  )
}

export function ChapterIV({ data }: { data: ReportV2Data }) {
  const rawStages: PlanStage[] = data.action_plan?.stages ?? []
  const stages = rawStages.filter(s => (s.items || []).length > 0)

  const headline = stages.length >= 2
    ? '从阶段一开始，一步步往下走。'
    : stages.length === 1
      ? '先把这几件具体的事做掉。'
      : '暂时还没有足够证据生成行动计划。'

  return (
    <div id="chapter-4">
      <ChapterOpener numeral="IV" label="下一步" headline={headline} />
      <Chapter>
        {stages.length === 0 ? (
          <p className="text-[15px] text-slate-500 leading-relaxed max-w-[60ch]">
            你的画像和成长档案里还没有足够的具体信号支撑行动建议——
            去记一条最近的学习笔记、项目进展或面试反思，再回来重新生成。
          </p>
        ) : (
          <div className="space-y-4">
            {stages.map((stage, i) => (
              <section key={i}>
                <StageHeader stage={stage} />
                <div className="mt-4">
                  {(stage.items || []).map((item, j) => (
                    <ActionArticle key={item.id || `${i}-${j}`} item={item} />
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </Chapter>
    </div>
  )
}
