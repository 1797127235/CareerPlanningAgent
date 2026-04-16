import type { ReportV2Data } from '@/api/report'

interface PrintFooterProps {
  data: ReportV2Data
}

export function PrintFooter({ data }: PrintFooterProps) {
  const date = new Date(data.generated_at).toISOString().slice(0, 10)
  return (
    <footer className="text-center" style={{ paddingTop: '10mm', paddingBottom: '18mm' }}>
      <p className="text-[10px] text-slate-400 tracking-wide">
        {data.target.label || '职业报告'} · 生成于 {date}
      </p>
    </footer>
  )
}
