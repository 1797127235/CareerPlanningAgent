interface EpilogueProps {
  generatedAt: string
  onRegenerate?: () => void
  regenerating?: boolean
}

export function Epilogue({ generatedAt, onRegenerate, regenerating }: EpilogueProps) {
  const date = new Date(generatedAt).toISOString().slice(0, 10)
  return (
    <footer className="pt-16 pb-12 border-t border-slate-200 mt-24">
      <p className="text-[13px] text-slate-400 italic tabular-nums">
        这份报告生成于 {date}。你每变一次成长记录，它也会跟着变。
      </p>
      {onRegenerate && (
        <button
          onClick={onRegenerate}
          disabled={regenerating}
          className="mt-5 inline-flex items-center gap-1 text-[13px] font-semibold text-slate-900 border-b-2 border-slate-900 pb-0.5 hover:text-blue-700 hover:border-blue-700 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-wait"
        >
          {regenerating ? '正在重新生成…' : '再生成一次 →'}
        </button>
      )}
    </footer>
  )
}
