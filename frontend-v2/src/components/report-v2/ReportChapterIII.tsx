import { Chapter, ChapterOpener, DropCap, PullQuote } from '@/components/editorial'
import type { ReportV2Data } from '@/api/report'

export function ReportChapterIII({ data }: { data: ReportV2Data }) {
  const sg = data.skill_gap || { top_missing: [], matched_skills: [] }
  const missing = sg.top_missing.slice(0, 3)
  const practiced = sg.matched_skills.filter((m) => m.status === 'practiced' || m.status === 'completed').slice(0, 4)

  const gapCount = missing.length || 2
  const heroTitle = (
    <>
      你已经接近了 — 还差 <strong>{gapCount === 1 ? '一件事' : `${gapCount} 件事`}</strong> 的距离。
    </>
  )

  const masteredText =
    practiced.length > 0
      ? `先来看你已经握在手里的东西：${practiced.map((m) => m.name).join('、')} 已经在你的项目或技能列表中有了对应痕迹。这不是从零开始，而是有基础地补缺口。`
      : `你目前的履历已经展示了一定的技术基础和学习意愿。这份报告不是要告诉你“你不行”，而是要帮你把已有的东西和未来需要的东西对齐。`

  const gapText =
    missing.length > 0
      ? `真正的差距在于：${missing.map((m) => m.name).join('、')}。这几项是目标岗位 JD 中出现频率较高的技能，而你的现有项目中缺少能直接对应的场景或证据。`
      : `从现有数据来看，没有特别突出的技能缺口。但这并不意味着可以高枕无忧——接下来需要的是把已有技能打磨得更深，并且用可量化的方式呈现出来。`

  const distanceText =
    missing.length > 0
      ? missing
          .map((m) => {
            if (m.fill_path === 'learn') return `${m.name} 可以通过一个系统性的学习 demo 补上`
            if (m.fill_path === 'practice') return `${m.name} 更适合在一个真实项目中实践一次`
            return `${m.name} 需要学习 + 实践双线并进`
          })
          .join('；') +
        '。这些都不是需要“一年”才能完成的改变，而是一个学期、甚至一个假期的刻意练习就能触达的距离。'
      : `继续保持现有项目的迭代节奏，同时补写 README、性能数据和测试说明，就能让同一份履历的含金量提升一个档次。`

  return (
    <>
      <ChapterOpener numeral="III" title={heroTitle} />
      <Chapter numeral="III" label="差距" title="">
        <DropCap>{masteredText}</DropCap>
        <p className="mt-6 text-[var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">{gapText}</p>
        <p className="mt-6 text-[var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">{distanceText}</p>
        <PullQuote>差距不是你不够 — 是你还没给自己机会碰到这些事。</PullQuote>
      </Chapter>
    </>
  )
}
