import type { AiSuggestion } from './mockData'

interface AiSuggestionsProps {
  suggestions: AiSuggestion[]
  onConvert: (text: string) => void
}

export function AiSuggestions({ suggestions, onConvert }: AiSuggestionsProps) {
  return (
    <div className="mt-3 p-3 rounded-[var(--radius-md)] bg-[var(--blue)]/[0.08] border border-[var(--blue)]/10">
      <p className="text-[12px] font-semibold text-[var(--blue)] mb-2">AI 建议</p>
      <div className="space-y-2">
        {suggestions.map((s, idx) => (
          <div key={idx} className="flex items-start justify-between gap-3">
            <span className="text-[13px] text-[var(--text-1)] leading-relaxed flex-1">
              {idx + 1}. {s.text}
            </span>
            <button
              onClick={() => onConvert(s.text)}
              className="shrink-0 text-[11px] font-medium text-[var(--blue)] hover:text-[var(--blue-deep)] cursor-pointer"
            >
              转为计划
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
