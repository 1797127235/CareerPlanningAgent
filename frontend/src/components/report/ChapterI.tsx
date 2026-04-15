import type { ReportV2Data } from '@/api/report'
import { ChapterOpener, Chapter, DropCap, PullQuote } from './index'
import { splitParagraphs, firstSentence } from './reportUtils'

export function ChapterI({ data }: { data: ReportV2Data }) {
  const narrative = data.narrative || ''
  const paragraphs = splitParagraphs(narrative, 2, 3)

  const fallback = [
    `你的履历里已经有${data.target.label}方向的技术痕迹，项目经历和技能标签正在慢慢拼成一条路径。`,
    `这些描述目前停留在"做了什么"，下次如果加上"做成了什么"的具体数字，会更有说服力。`,
    `现有项目里再补一些量化数据和技术文档，面试时会更容易被看到。`,
  ]

  const paras = paragraphs.length >= 2 ? paragraphs : fallback

  const diag = data.diagnosis || []
  const quote =
    diag.find((d) => d.status === 'pass' && d.current_text?.length > 10) ??
    diag.find((d) => d.current_text?.length > 10)
  const quoteText = quote
    ? quote.current_text.length > 60
      ? quote.current_text.slice(0, 60) + '…'
      : quote.current_text
    : null
  const quoteSource = quote?.source ?? '你的成长轨迹'

  const headline = firstSentence(paras[0]) || `你像是一个在${data.target.label}方向持续探索的人。`

  return (
    <div id="chapter-1">
      <ChapterOpener numeral="I" label="你是谁" headline={headline} />
      <Chapter>
        <DropCap>{paras[0]}</DropCap>
        {paras[1] && <p className="mt-5">{paras[1]}</p>}
        {paras[2] && <p className="mt-5">{paras[2]}</p>}
        {quoteText ? (
          <PullQuote attribution={`摘自你的「${quoteSource}」`}>{quoteText}</PullQuote>
        ) : (
          <PullQuote>先把自己正在做的记下来 —— 回看时你会看到自己走了多远。</PullQuote>
        )}
        {paras[3] && <p className="mt-5">{paras[3]}</p>}
        {paras[4] && <p className="mt-5">{paras[4]}</p>}
      </Chapter>
    </div>
  )
}
