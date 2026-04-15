import { bucketOf } from '@/lib/resultTypeBuckets'
import type { CoachResultDetail } from '@/types/coach'

export function CoachResultEpilogue({ data }: { data: CoachResultDetail }) {
  const isStructured = !!data.detail?._structured
  const bucket = bucketOf(data.result_type, isStructured)

  let closing = ''
  if (bucket === 'diagnosis') {
    closing = 'JD 会换，要求会变，但你的技能栈只会越来越清晰。'
  } else if (bucket === 'narrative') {
    closing = '这份报告不是终点，而是你下一步行动的起点。'
  } else if (bucket === 'review') {
    closing = '每一次复盘，都会让下一次表现更好一点。'
  } else {
    closing = '保持记录，时间会给出答案。'
  }

  return (
    <section className="relative py-16 md:py-24 text-center">
      <div className="max-w-[58ch] mx-auto">
        <p className="font-sans text-[length:var(--fs-body)] leading-[var(--lh-body-zh)] text-[var(--ink-2)] italic">
          {closing}
        </p>
        <p className="mt-6 font-mono text-[length:var(--fs-caption)] text-[var(--ink-3)]">
          generated at {data.created_at ? data.created_at.slice(0, 10) : '—'}
        </p>
      </div>
    </section>
  )
}
