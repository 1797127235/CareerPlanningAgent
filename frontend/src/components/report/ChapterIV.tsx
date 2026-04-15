import { useNavigate } from 'react-router-dom'
import type { ReportV2Data, PlanActionItem } from '@/api/report'
import { ChapterOpener, Chapter } from './index'
import { firstSentence } from './reportUtils'

const TYPE_LABEL: Record<string, string> = {
  skill: '技能',
  project: '项目',
  job_prep: '求职',
}

function ActionArticle({ item }: { item: PlanActionItem }) {
  const navigate = useNavigate()
  return (
    <article className="pt-5 border-t-2 border-slate-900">
      <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500 mb-3">
        {TYPE_LABEL[item.type] ?? '行动'}
        {item.priority === 'high' && (
          <>
            <span className="mx-1.5 text-slate-300">·</span>
            <span className="text-blue-600">优先</span>
          </>
        )}
      </p>
      <h3 className="text-[22px] font-bold text-slate-900 leading-[1.15] tracking-tight">
        {item.tag || firstSentence(item.text)}
      </h3>
      <p className="mt-2 text-[14px] text-slate-600 leading-relaxed max-w-[60ch]">{item.text}</p>
      <button
        onClick={() => navigate('/growth-log', { state: { prefill: item.text } })}
        className="mt-4 inline-flex items-center gap-1 text-[13px] font-semibold text-slate-900 border-b-2 border-slate-900 pb-0.5 hover:text-blue-700 hover:border-blue-700 transition-colors cursor-pointer"
      >
        记到成长档案 →
      </button>
    </article>
  )
}

export function ChapterIV({ data }: { data: ReportV2Data }) {
  const ap = data.action_plan
  const pool: PlanActionItem[] = [
    ...(ap?.skills ?? []),
    ...(ap?.project ?? []),
    ...(ap?.job_prep ?? []),
  ]
  // prioritize high-priority items, keep at most 3
  const sorted = pool.sort((a, b) => {
    if (a.priority === 'high' && b.priority !== 'high') return -1
    if (a.priority !== 'high' && b.priority === 'high') return 1
    return 0
  })
  const items = sorted.slice(0, 3)

  return (
    <div id="chapter-4">
      <ChapterOpener numeral="IV" label="下一步" headline="先从这一件开始。" />
      <Chapter>
        {items.length === 0 ? (
          <p className="text-[15px] text-slate-500">
            行动方案正在生成中。你可以先回到岗位图谱，了解目标方向需要哪些核心技能。
          </p>
        ) : (
          <div className="space-y-12">
            {items.map((item, i) => (
              <ActionArticle key={item.id || i} item={item} />
            ))}
          </div>
        )}
      </Chapter>
    </div>
  )
}
