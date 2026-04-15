import { Chapter, ChapterOpener, DropCap, PullQuote } from '@/components/editorial'
import type { ReportV2Data } from '@/api/report'

function splitParagraphs(text: string, minSentences = 2, maxSentences = 3): string[] {
  if (!text || text.trim().length < 10) return []
  const byNewline = text
    .split(/\n+/)
    .map((s) => s.trim())
    .filter(Boolean)
  if (byNewline.length >= 2) return byNewline

  const sentences = text.match(/[^。！？.!?]+[。！？.!?]+/g) || [text]
  const out: string[] = []
  let i = 0
  while (i < sentences.length) {
    const chunkSize = Math.min(maxSentences, Math.max(minSentences, sentences.length - i))
    out.push(sentences.slice(i, i + chunkSize).join('').trim())
    i += chunkSize
  }
  return out.filter(Boolean)
}

function extractFirstSentence(text: string): string {
  const m = text.match(/^[^。！？.!?]+[。！？.!?]?/)
  return m ? m[0].trim() : text.trim()
}

export function ReportChapterI({ data }: { data: ReportV2Data }) {
  const narrative = data.narrative || ''
  const headlineRaw = extractFirstSentence(narrative)
  const headline =
    headlineRaw.length >= 10
      ? headlineRaw
      : `你像是一个在${data.target.label}方向上持续探索的人。`

  const paragraphs = splitParagraphs(narrative, 2, 3)

  // Fallback paragraphs if narrative is too short or failed
  const fallbackParagraphs = [
    `你的履历里已经有${data.target.label}相关的技术痕迹，项目经历和技能标签正在慢慢拼成一条路径。`,
    `这些描述目前停留在“做了什么”，下次如果加上“做成了什么”的具体数字，会更有说服力。`,
    `现有项目里若再补一些量化数据和技术文档，面试时会更容易被看到。`,
  ]

  const displayParagraphs = paragraphs.length >= 2 ? paragraphs : fallbackParagraphs

  // Build PullQuote from diagnosis (resume/growth_log project text)
  const diagnosis = data.diagnosis || []
  const quoteCandidate =
    diagnosis.find((d) => d.status === 'pass' && d.current_text?.length > 10) ||
    diagnosis.find((d) => d.current_text?.length > 10)

  const quoteText = quoteCandidate
    ? quoteCandidate.current_text.slice(0, 60) + (quoteCandidate.current_text.length > 60 ? '…' : '')
    : null

  const quoteSource = quoteCandidate ? quoteCandidate.source : '你的成长轨迹'

  return (
    <>
      <ChapterOpener numeral="I" title={<>{headline}</>} />
      <Chapter numeral="I" label="你是谁">
        <DropCap>{displayParagraphs[0]}</DropCap>
        {displayParagraphs[1] && <p className="mt-6 text-[var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">{displayParagraphs[1]}</p>}
        {displayParagraphs[2] && <p className="mt-6 text-[var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">{displayParagraphs[2]}</p>}
        {quoteText ? (
          <PullQuote attribution={`来自你填写的「${quoteSource}」`}>{quoteText}</PullQuote>
        ) : (
          <PullQuote>先把自己正在做的记下来 — 回看时你会看到自己走了多远。</PullQuote>
        )}
        {displayParagraphs[3] && <p className="mt-6 text-[var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">{displayParagraphs[3]}</p>}
        {displayParagraphs[4] && <p className="mt-6 text-[var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)]">{displayParagraphs[4]}</p>}
      </Chapter>
    </>
  )
}
