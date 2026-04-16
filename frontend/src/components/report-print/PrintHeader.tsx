import type { ReportV2Data } from '@/api/report'
import { fitHeadline } from './utils/fitHeadline'
import { useEffect, useRef, useState } from 'react'

interface PrintHeaderProps {
  data: ReportV2Data
}

export function PrintHeader({ data }: PrintHeaderProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [headlineSize, setHeadlineSize] = useState(60)

  useEffect(() => {
    if (!ref.current) return
    const w = ref.current.offsetWidth
    const size = fitHeadline(
      data.target.label || '职业报告',
      'Source Han Serif SC',
      700,
      w,
      1,
      36,
      56,
    )
    setHeadlineSize(size)
  }, [data.target.label])

  const date = new Date(data.generated_at).toISOString().slice(0, 10)

  return (
    <header ref={ref} style={{ paddingTop: '18mm', paddingBottom: '12mm' }}>
      <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500 mb-4">
        职业生涯发展报告
      </p>
      <h1
        className="font-bold text-slate-900 leading-[1.05]"
        style={{
          fontSize: headlineSize,
          fontFamily: '"Source Han Serif SC", serif',
        }}
      >
        {data.target.label || '职业报告'}
      </h1>
      <p className="mt-8 text-[10px] text-slate-400 text-right tracking-wide">
        生成日期 {date}
      </p>
    </header>
  )
}
