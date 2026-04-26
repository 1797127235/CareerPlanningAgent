import { Chapter, ChapterOpener, DropCap, PullQuote } from '@/components/editorial'
import type { ReportV2Data } from '@/api/report'

function splitParagraphs(text: string, minSentences = 2, maxSentences = 3): string[] {
  if (!text || text.trim().length < 10) return []

  const byNewline = text
    .split(/\n+/)
    .map((s) => s.trim())
    .filter(Boolean)

  if (byNewline.length >= 2) return byNewline

  const sentences = text.match(/[^。！？!?]+[。！？!?]?/g) || [text]
  const out: string[] = []
  let i = 0

  while (i < sentences.length) {
    const remaining = sentences.length - i
    const chunkSize = Math.min(maxSentences, Math.max(minSentences, remaining))
    out.push(sentences.slice(i, i + chunkSize).join('').trim())
    i += chunkSize
  }

  return out.filter(Boolean)
}

function extractFirstSentence(text: string): string {
  const match = text.match(/^[^。！？!?]+[。！？!?]?/)
  return match ? match[0].trim() : text.trim()
}

export function ReportChapterI({ data }: { data: ReportV2Data }) {
  const narrative = data.narrative || ''
  const headlineRaw = extractFirstSentence(narrative)
  const headline =
    headlineRaw.length >= 10
      ? headlineRaw
      : `你像一个在 ${data.target.label} 方向上持续摸索的人。`

  const paragraphs = splitParagraphs(narrative, 2, 3)

  const fallbackParagraphs = [
    `你的履历里已经有一些和 ${data.target.label} 相关的痕迹，项目经历和技能标签正在慢慢拼成一条路。`,
    '这些描述目前更多停留在“做了什么”，如果再补上一点“做成了什么”的量化结果，整段经历会更有说服力。',
    '把项目中的性能数据、对比结果和关键取舍写出来，你的能力会更容易被看见。',
  ]

  const displayParagraphs = paragraphs.length >= 2 ? paragraphs : fallbackParagraphs

  const diagnosis = data.diagnosis || []
  const quoteCandidate =
    diagnosis.find((item) => item.status === 'pass' && item.current_text?.length > 10) ||
    diagnosis.find((item) => item.current_text?.length > 10)

  const quoteText = quoteCandidate
    ? quoteCandidate.current_text.slice(0, 60) + (quoteCandidate.current_text.length > 60 ? '…' : '')
    : null

  const quoteSource = quoteCandidate ? quoteCandidate.source : '你的成长轨迹'

  return (
    <>
      <ChapterOpener
        numeral="I"
        title={<>{headline}</>}
        variant="display"
        tone="book"
        titleClassName="text-[clamp(36px,4.6vw,60px)] leading-[1.16] max-w-[12ch] md:max-w-[13ch]"
      />
      <Chapter numeral="I" label="你是谁" compact bodyClassName="max-w-[44rem]">
        <DropCap>{displayParagraphs[0]}</DropCap>
        {displayParagraphs[1] && (
          <p className="mt-4 text-[length:var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">
            {displayParagraphs[1]}
          </p>
        )}
        {displayParagraphs[2] && (
          <p className="mt-4 text-[length:var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">
            {displayParagraphs[2]}
          </p>
        )}
        {quoteText ? (
          <PullQuote variant="book" attribution={`来自你填写的「${quoteSource}」`}>
            {quoteText}
          </PullQuote>
        ) : (
          <PullQuote variant="book">
            先把自己正在做的记下来 —— 回看时你会看到自己走了多远。
          </PullQuote>
        )}
        {displayParagraphs[3] && (
          <p className="mt-4 text-[length:var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">
            {displayParagraphs[3]}
          </p>
        )}
        {displayParagraphs[4] && (
          <p className="mt-4 text-[length:var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">
            {displayParagraphs[4]}
          </p>
        )}
      </Chapter>
    </>
  )
}
