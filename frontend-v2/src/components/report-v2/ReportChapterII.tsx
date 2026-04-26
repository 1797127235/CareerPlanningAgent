import { useNavigate } from 'react-router-dom'
import { Chapter, ChapterOpener, DropCap } from '@/components/editorial'
import type { ReportV2Data } from '@/api/report'

export function ReportChapterII({ data }: { data: ReportV2Data }) {
  const navigate = useNavigate()
  const targetLabel = data.target.label
  const alignment = data.career_alignment || { observations: '', alignments: [], cannot_judge: [] }

  const heroTitle = (
    <>
      <strong>{targetLabel}</strong> 这条路，和你契合的是 <strong>把复杂拆成简单</strong> 的那部分。
    </>
  )

  const whyThis =
    alignment.observations ||
    `从现有履历来看，${targetLabel} 和你的技能路径有较高重合度。你已经在项目中碰到过这条路最核心的工程问题。`

  const dailyWhat =
    data.ai_impact_narrative ||
    data.differentiation_advice ||
    '这个方向的日常，不是追逐最新框架，而是在复杂约束下写出稳定、可维护且高性能的代码。'

  const notRecommended =
    alignment.cannot_judge?.length > 0
      ? `也有一些维度暂时还无法从你的履历里判断，比如 ${alignment.cannot_judge.slice(0, 2).join('、')}。这意味着你还需要通过更完整的项目或真实实践，去验证自己是否真的适合这条路。`
      : '如果回看你的项目经历，会发现可量化结果和系统化证据还不够多。这是现在最值得补齐的地方。'

  const altRoles = alignment.alignments
    .filter((item) => item.node_id !== data.target.node_id)
    .slice(0, 2)

  const altText =
    altRoles.length > 0
      ? `另外，${altRoles.map((item) => item.label).join('、')} 也可以作为备选方向。${altRoles[0]?.gap || '建议把它们和当前目标放在一起对比，再决定主攻哪一条。'}`
      : '当然，技术路径并不是唯一答案。如果你在深入过程中发现自己对工程实现细节的兴趣没有想象中高，也可以延展到相邻方向。'

  return (
    <>
      <ChapterOpener numeral="II" title={heroTitle} variant="chapter" tone="book" />
      <Chapter numeral="II" label="你能去哪" compact bodyClassName="max-w-[44rem]">
        <DropCap>{whyThis}</DropCap>
        <p className="mt-4 text-[length:var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">
          {dailyWhat}
        </p>
        <p className="mt-4 text-[length:var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">
          {notRecommended}
        </p>
        <p className="mt-4 text-[length:var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">
          {altText}
        </p>
        <div className="mt-8">
          <button
            onClick={() => navigate(`/graph?target=${encodeURIComponent(data.target.node_id)}`)}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full border border-[var(--line)] text-[var(--ink-1)] hover:bg-[var(--line)]/10 transition-colors text-sm font-medium"
          >
            去图谱看看这条路径 →
          </button>
        </div>
      </Chapter>
    </>
  )
}
