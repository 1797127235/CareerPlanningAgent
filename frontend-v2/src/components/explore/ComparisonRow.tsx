interface Props {
  label: string
  leftText: string
  rightText: string
}

export function ComparisonRow({ label, leftText, rightText }: Props) {
  return (
    <div>
      <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500 mb-4">
        {label}
      </p>
      <div className="grid grid-cols-2 gap-6">
        <p className="text-[14px] leading-relaxed text-slate-900">{leftText}</p>
        <p className="text-[14px] leading-relaxed text-slate-900">{rightText}</p>
      </div>
    </div>
  )
}
