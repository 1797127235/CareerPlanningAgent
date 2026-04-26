import { Chapter, ChapterOpener, DropCap, PullQuote } from '@/components/editorial'
import type { ReportV2Data } from '@/api/report'

export function ReportChapterIII({ data }: { data: ReportV2Data }) {
  const skillGap = data.skill_gap || { top_missing: [], matched_skills: [] }
  const missing = skillGap.top_missing.slice(0, 3)
  const practiced = skillGap.matched_skills
    .filter((item) => item.status === 'practiced' || item.status === 'completed')
    .slice(0, 4)

  const gapCount = missing.length || 2
  const heroTitle = (
    <>
      你已经接近了——还差 <strong>{gapCount === 1 ? '1 件事' : `${gapCount} 件事`}</strong> 的距离。
    </>
  )

  const masteredText =
    practiced.length > 0
      ? `先看你已经握在手里的东西：${practiced.map((item) => item.name).join('、')}。这些不是“从零开始”，而是已经有了可以继续往前推的基础。`
      : '你现在的履历已经展示出一定的技术基础和学习意愿。这份报告不是为了告诉你“不行”，而是为了把已有的东西和接下来要补的东西对齐。'

  const gapText =
    missing.length > 0
      ? `真正的差距在于：${missing.map((item) => item.name).join('、')}。这些能力在目标岗位里出现频率较高，但你现有项目里还缺少足够直接的场景或证据。`
      : '从现在的数据看，没有特别突出的硬伤；但下一步依然需要把已有能力打磨得更深，并且用更可量化的方式表达出来。'

  const distanceText =
    missing.length > 0
      ? missing
          .map((item) => {
            if (item.fill_path === 'learn') return `${item.name} 更适合通过系统学习和一个小 demo 补上`
            if (item.fill_path === 'practice') return `${item.name} 更适合在真实项目里实践一次`
            return `${item.name} 需要学习和实践一起推进`
          })
          .join('；') + '。这些并不是一年以后才能完成的改变，而是一段刻意练习就能明显缩短的距离。'
      : '继续保持项目迭代节奏，同时补写 README、性能数据和测试说明，就能让同一份经历的含金量明显提升。'

  return (
    <>
      <ChapterOpener numeral="III" title={heroTitle} variant="chapter" tone="book" />
      <Chapter numeral="III" label="差距" compact bodyClassName="max-w-[44rem]">
        <DropCap>{masteredText}</DropCap>
        <p className="mt-4 text-[length:var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">
          {gapText}
        </p>
        <p className="mt-4 text-[length:var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">
          {distanceText}
        </p>
        <PullQuote variant="book">
          差距不是你不够 —— 是你还没给自己机会碰到这些事。
        </PullQuote>
      </Chapter>
    </>
  )
}
