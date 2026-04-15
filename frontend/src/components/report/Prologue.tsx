interface PrologueProps {
  target: { label: string; zone?: string }
  generatedAt: string
  onRegenerate?: () => void
  regenerating?: boolean
}

function fmtDate(iso: string): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  return d.toISOString().slice(0, 10)
}

export function Prologue({ target, generatedAt, onRegenerate, regenerating }: PrologueProps) {
  const date = fmtDate(generatedAt)
  return (
    <header className="pt-6 md:pt-8 pb-4">
      <p className="flex items-center gap-2 text-[11px] font-bold tracking-[0.22em] uppercase text-slate-400 mb-3">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-500" />
        职业生涯发展报告
      </p>
      <h1 className="text-[40px] md:text-[52px] lg:text-[60px] font-extrabold leading-[0.95] tracking-[-0.02em] text-slate-900">
        {target.label}
      </h1>
      <div className="mt-6 flex items-center gap-5 text-[12px] text-slate-500">
        <span className="tabular-nums">生成于 {date}</span>
        {onRegenerate && (
          <button
            onClick={onRegenerate}
            disabled={regenerating}
            className="font-semibold text-slate-900 border-b-2 border-slate-900 pb-0.5 hover:border-blue-700 hover:text-blue-700 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-wait print:hidden"
          >
            {regenerating ? '正在重新生成…' : '再生成 →'}
          </button>
        )}
      </div>
    </header>
  )
}
