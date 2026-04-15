import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Kicker, ChapterOpener } from '@/components/editorial'
import { bucketOf, typeLabelOf } from '@/lib/resultTypeBuckets'
import type { CoachResultDetail } from '@/types/coach'

export function CoachResultPrologue({ data }: { data: CoachResultDetail }) {
  const navigate = useNavigate()
  const isStructured = !!data.detail?._structured
  const bucket = bucketOf(data.result_type, isStructured)
  const bucketLabel = typeLabelOf(data.result_type)
  const jdTitle = (data.detail?.jd_title as string) || data.title || ''

  const heroTitle = bucket === 'diagnosis' && jdTitle
    ? `关于「${jdTitle}」`
    : data.title

  return (
    <div className="pt-8 pb-4">
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1.5 text-[length:var(--fs-body-sm)] text-[var(--ink-3)] hover:text-[var(--ink-1)] transition-colors mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        返回
      </button>

      <Kicker>EDITORIAL · {bucketLabel}</Kicker>
      <ChapterOpener numeral="·" title={heroTitle} />

      <p className="mt-4 font-sans text-[length:var(--fs-body-sm)] text-[var(--ink-3)]">
        {data.created_at?.slice(0, 10)}
      </p>
    </div>
  )
}
