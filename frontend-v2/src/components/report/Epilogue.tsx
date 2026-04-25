import { Sparkles } from 'lucide-react'

interface EpilogueProps {
  generatedAt: string
  onRegenerate?: () => void
  regenerating?: boolean
  onExport?: () => void
  onPolish?: () => void
  polishing?: boolean
}

export function Epilogue({ generatedAt, onRegenerate, regenerating, onExport, onPolish, polishing }: EpilogueProps) {
  const _d = new Date(generatedAt)
  const date = `${_d.getFullYear()}-${String(_d.getMonth() + 1).padStart(2, '0')}-${String(_d.getDate()).padStart(2, '0')}`
  return (
    <footer className="pt-16 pb-12 border-t border-slate-200 mt-24">
      <p className="text-[13px] text-slate-400 italic tabular-nums">
        这份报告生成于 {date}。你每变一次成长记录，它也会跟着变。
      </p>
      <div className="mt-5 flex items-center gap-5 flex-wrap print:hidden">
        {onRegenerate && (
          <button
            onClick={onRegenerate}
            disabled={regenerating}
            className="inline-flex items-center gap-1 text-[13px] font-semibold text-slate-900 border-b-2 border-slate-900 pb-0.5 hover:text-blue-700 hover:border-blue-700 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-wait"
          >
            {regenerating ? '正在重新生成…' : '再生成一次 →'}
          </button>
        )}
        {onPolish && (
          <button
            onClick={onPolish}
            disabled={polishing}
            className="inline-flex items-center gap-2 text-[13px] font-semibold text-slate-600 hover:text-blue-700 transition-colors cursor-pointer disabled:opacity-50"
          >
            <Sparkles className="w-3.5 h-3.5" />
            {polishing ? '润色中…' : '智能润色'}
          </button>
        )}
        {onExport && (
          <button
            onClick={onExport}
            className="inline-flex items-center gap-1 text-[13px] font-medium text-slate-600 border-b-2 border-transparent hover:text-slate-900 hover:border-slate-300 pb-0.5 transition-colors cursor-pointer"
          >
            导出 PDF →
          </button>
        )}
      </div>
    </footer>
  )
}
