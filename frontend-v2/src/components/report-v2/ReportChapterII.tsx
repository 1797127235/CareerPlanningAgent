import { useNavigate } from 'react-router-dom'
import { Chapter, ChapterOpener, DropCap } from '@/components/editorial'
import type { ReportV2Data } from '@/api/report'

export function ReportChapterII({ data }: { data: ReportV2Data }) {
  const navigate = useNavigate()
  const targetLabel = data.target.label
  const alignment = data.career_alignment || { observations: '', alignments: [], cannot_judge: [] }

  const heroTitle = (
    <>
      <strong>{targetLabel}</strong> 这条路，和你契合的是{' '}
      <strong>把复杂拆成简单</strong> 的那部分。
    </>
  )

  const whyThis =
    alignment.observations ||
    `从现有履历来看，${targetLabel} 与你的技能路径有较高的重叠度。你的项目经历中已经触及该方向所需的部分核心技术栈。`

  const dailyWhat =
    data.ai_impact_narrative ||
    data.differentiation_advice ||
    `这个方向的日常，不是追逐最新的技术热点，而是在约束条件下找到稳定、可维护的解决方案。系统思维和动手能力同样重要。`

  const notRecommended =
    alignment.cannot_judge?.length > 0
      ? `有些维度目前无法从你的履历中判断——比如 ${alignment.cannot_judge.slice(0, 2).join('、')}。这意味着短期内你需要通过实习或更完整的项目来验证自己是否真的适合这条路。`
      : `如果回顾你的项目经历，发现缺少可量化的成果和系统性的技术文档，那么在面试中很容易被追问“你到底做了什么”。这是目前最需要补齐的地方。`

  const altRoles = alignment.alignments
    .filter((a) => a.node_id !== data.target.node_id)
    .slice(0, 2)

  const altText =
    altRoles.length > 0
      ? `另外，${altRoles.map((a) => a.label).join('、')} 也是可以考虑的次选方向。${altRoles[0].gap || '建议对比两者的技能要求差异，再决定主攻哪一条路径。'}`
      : `当然，技术路径不是唯一的。如果在深入过程中发现自己对工程实现细节的兴趣不如预期，也可以向上下游方向（如技术产品、基础设施）延伸。`

  return (
    <>
      <ChapterOpener numeral="II" title={heroTitle} />
      <Chapter numeral="II" label="你能去哪" title="">
        <DropCap>{whyThis}</DropCap>
        <p className="mt-4 text-[var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">{dailyWhat}</p>
        <p className="mt-4 text-[var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">{notRecommended}</p>
        <p className="mt-4 text-[var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">{altText}</p>
        <div className="mt-10">
          <button
            onClick={() => navigate(`/graph?target=${encodeURIComponent(data.target.node_id)}`)}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full border border-[var(--line)] text-[var(--ink-1)] hover:bg-[var(--line)]/10 transition-colors text-sm font-medium"
          >
            去图谱看这个路径 →
          </button>
        </div>
      </Chapter>
    </>
  )
}
