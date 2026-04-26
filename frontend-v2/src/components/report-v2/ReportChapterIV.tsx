import { useNavigate } from 'react-router-dom'
import { Chapter, ChapterOpener } from '@/components/editorial'
import type { ReportV2Data, PlanActionItem } from '@/api/report'

const numerals = ['一', '二', '三']

function ActionCard({ idx, item }: { idx: number; item: PlanActionItem }) {
  const navigate = useNavigate()

  return (
    <div className="mt-8 first:mt-4 rounded-[24px] border border-[var(--line)] bg-[var(--bg-card)] px-6 py-5 shadow-[var(--shadow-block)]">
      <h3
        className="text-[clamp(24px,2.8vw,34px)] leading-[1.25] text-[var(--ink-1)]"
        style={{ fontFamily: 'var(--font-serif)' }}
      >
        {numerals[idx]} · {item.tag || '这周先做这件事'}
      </h3>
      <p className="mt-3 text-[length:var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-2)]">
        {item.text}
      </p>
      {item.deliverable && (
        <p className="mt-3 text-[length:var(--fs-body)] leading-[var(--lh-body-zh)] text-[var(--ink-3)]">
          预期产出：{item.deliverable}
        </p>
      )}
      <p className="mt-2 text-[length:var(--fs-body)] leading-[var(--lh-body-zh)] text-[var(--ink-3)]">
        优先级：{item.priority === 'high' ? '高' : '中'} · 阶段：{item.phase || 1}
      </p>
      <button
        onClick={() => navigate('/growth-log', { state: { prefill: item.text } })}
        className="mt-5 inline-flex items-center gap-2 px-5 py-2.5 rounded-full border border-[var(--line)] text-[var(--ink-1)] hover:bg-[var(--line)]/10 transition-colors text-sm font-medium"
      >
        记到成长档案 →
      </button>
    </div>
  )
}

export function ReportChapterIV({ data }: { data: ReportV2Data }) {
  const stages = data.action_plan?.stages || []
  const allItems = stages.flatMap((stage) => stage.items || [])
  const items = allItems.slice(0, 3)

  return (
    <>
      <ChapterOpener numeral="IV" title={<>先从 <strong>这一件</strong> 开始。</>} variant="chapter" tone="book" />
      <Chapter numeral="IV" label="下一步" compact bodyClassName="max-w-[44rem]">
        {items.length === 0 ? (
          <p className="text-[length:var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-2)]">
            行动建议还在生成中。你可以先回到岗位图谱，继续确认目标方向真正需要的核心能力。
          </p>
        ) : (
          items.map((item, i) => <ActionCard key={item.id || i} idx={i} item={item} />)
        )}
      </Chapter>
    </>
  )
}
