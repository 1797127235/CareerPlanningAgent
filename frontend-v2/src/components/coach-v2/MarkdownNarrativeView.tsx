import { Chapter, PullQuote } from '@/components/editorial'
import { EditorialMarkdown } from './EditorialMarkdown'
import { sanitizeAiMarkdown } from '@/lib/sanitizeAiMarkdown'
import type { CoachResultDetail } from '@/types/coach'

export function MarkdownNarrativeView({ data }: { data: CoachResultDetail }) {
  const raw = (data.detail?.raw_text as string) || ''
  const cleaned = sanitizeAiMarkdown(raw)

  return (
    <Chapter numeral="I" label="全文" title={data.title}>
      {data.summary && (
        <PullQuote>{data.summary}</PullQuote>
      )}
      <div className="mt-4">
        <EditorialMarkdown source={cleaned} />
      </div>
    </Chapter>
  )
}
